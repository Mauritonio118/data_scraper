from __future__ import annotations

import asyncio
import gzip
import time
import zlib
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
import brotli
import httpx


@dataclass(frozen=True)
class HTTPSettings:
    """
    Central configuration for HTTP fetching behavior.

    Why a dataclass
    - It groups all tunables in a single place.
    - It makes defaults explicit.
    - It allows passing a custom settings object per call.

    Fields
    - timeout_seconds: total timeout per request.
    - max_retries: how many attempts before giving up.
    - backoff_base_seconds: base for exponential backoff between retries.
    - backoff_max_seconds: max sleep time between retries.
    - follow_redirects: whether httpx should follow 3xx responses.
    - max_response_bytes: safety cap to avoid huge downloads.
    - requests_per_host_per_second: soft rate limit per host.
    - user_agent: browser like User-Agent string.
    """
    timeout_seconds: float = 25.0
    max_retries: int = 3
    backoff_base_seconds: float = 0.8
    backoff_max_seconds: float = 8.0
    follow_redirects: bool = True
    max_response_bytes: int = 15_000_000
    requests_per_host_per_second: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )


class RequestHTTPError(Exception):
    """
    Custom exception for request failures.

    Why have a custom exception
    - Lets callers catch a single error type for fetch failures.
    - Keeps error messages consistent.
    """
    pass


@dataclass(frozen=True)
class CompressedHTTPResult:
    """
    Represents a raw HTTP result that may include a compressed body.

    Notes
    - body is raw bytes exactly as returned by the HTTP client.
    - headers are stored as a plain dict for easy access.
    - final_url is the last URL after redirects.
    """
    url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    body: bytes


class HostRateLimiter:
    """
    Very small per host rate limiter.

    What it does
    - Ensures that requests to the same host are spaced out.
    - Helps reduce accidental overload.

    How it works
    - Stores last request time per host.
    - If the time since last request is smaller than min_interval it sleeps.
    """

    def __init__(self, rps_per_host: float) -> None:
        # Convert requests per second into minimum seconds between requests.
        self.min_interval = 1.0 / max(rps_per_host, 0.0001)
        self._last_by_host: dict[str, float] = {}

    async def wait(self, host: str) -> None:
        """
        Wait until it is safe to send the next request to this host.

        Steps
        1) Read current monotonic time.
        2) Compute elapsed time since last request to this host.
        3) Sleep if needed.
        4) Record the time for the next call.
        """
        now = time.monotonic()
        last = self._last_by_host.get(host, 0.0)
        elapsed = now - last

        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)

        self._last_by_host[host] = time.monotonic()


def _normalize_url(url: str) -> str:
    """
    Normalize a raw URL into something httpx can reliably request.

    Behavior
    - Strips whitespace.
    - Converts protocol relative URLs like //example.com to https://example.com
    - Adds https:// if no scheme is provided.

    Returns
    - Normalized URL string.
    - Empty string if input was empty or whitespace.
    """
    u = (url or "").strip()
    if not u:
        return ""

    # Handle protocol relative URLs.
    if u.startswith("//"):
        return "https:" + u

    parsed = urlparse(u)

    # If scheme is missing default to https.
    if not parsed.scheme:
        return "https://" + u

    return u


def _default_headers(settings: HTTPSettings, referer: Optional[str] = None) -> dict[str, str]:
    """
    Build a set of default HTTP headers.

    Goal
    - Provide reasonable browser like headers.
    - Improve compatibility for servers that check header presence.

    Notes
    - This is not meant to bypass protections.
    - It is meant to look like a normal browser request.

    referer
    - If provided it is included as Referer header.
    """
    h = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    }
    if referer:
        h["Referer"] = referer
    return h


def _looks_like_html(content_type: Optional[str]) -> bool:
    """
    Lightweight check to decide whether the response is likely HTML.

    Returns
    - True when content_type is missing or indicates html or xhtml.
    - False otherwise.
    """
    if not content_type:
        return True

    ct = content_type.lower()
    if "text/html" in ct:
        return True
    if "application/xhtml+xml" in ct:
        return True

    return False


def _decode_response_bytes(content: bytes, headers: dict[str, str]) -> str:
    """
    Convert raw response bytes into a text string.

    Decoding strategy
    1) If Content-Type contains charset try that first.
    2) Otherwise try a small set of common encodings.
    3) Fallback to utf-8 with replacement.

    Returns
    - Decoded text with errors replaced.
    """
    encoding = None
    ctype = headers.get("content-type") or ""
    ctype_low = ctype.lower()

    if "charset=" in ctype_low:
        try:
            encoding = ctype_low.split("charset=", 1)[1].split(";", 1)[0].strip()
        except Exception:
            encoding = None

    if encoding:
        try:
            return content.decode(encoding, errors="replace")
        except Exception:
            pass

    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(enc, errors="replace")
        except Exception:
            continue

    return content.decode("utf-8", errors="replace")


def decompress_html_result(result: CompressedHTTPResult) -> str:
    """
    Decompress a CompressedHTTPResult into final HTML text.

    Problem this solves
    - Some environments return already decoded bodies even when headers still say br.
    - Attempting brotli.decompress on plain HTML triggers brotli decoder errors.

    Strategy
    - First sniff the body. If it already looks like HTML, skip decompression.
    - Otherwise, attempt decompression based on Content-Encoding.
    - If decompression fails, fall back to raw bytes.
    - Finally decode bytes to text using charset hints from Content-Type.
    """
    raw = result.body or b""

    # Fast sniffing: if body already looks like HTML, do not decompress.
    # This covers cases like your reity.cl response.
    head = raw[:256].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html") or b"<html" in head:
        return _decode_response_bytes(raw, result.headers)

    enc = (result.headers.get("content-encoding") or "").lower().strip()

    # Decompress best effort. Never crash if headers lie.
    if "br" in enc:
        try:
            import brotli  # type: ignore
            raw = brotli.decompress(raw)
        except Exception:
            pass

    elif "gzip" in enc:
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass

    elif "deflate" in enc:
        try:
            raw = zlib.decompress(raw)
        except Exception:
            try:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                pass

    return _decode_response_bytes(raw, result.headers)



async def fetch_html_compressed(
    url: str,
    *,
    settings: HTTPSettings | None = None,
    referer: Optional[str] = None,
    render_js: bool = False,
    wait_until: str = "networkidle",
    js_timeout_ms: int = 30_000,
) -> CompressedHTTPResult:
    """
    Fetch a URL and return a potentially compressed HTTP body.

    Purpose
    - This function returns raw bytes plus headers.
    - Caller can decide when to decompress.

    Main modes
    - render_js=False uses httpx and returns the raw body as received.
    - render_js=True uses Playwright and returns UTF-8 bytes of page.content().

    Returns
    - CompressedHTTPResult containing url, final_url, status_code, headers, body.

    Raises
    - RequestHTTPError when the request cannot be completed.
    """
    s = settings or HTTPSettings()
    normalized = _normalize_url(url)
    if not normalized:
        raise RequestHTTPError("URL vacía")

    host = urlparse(normalized).netloc.lower()

    limiter = getattr(fetch_html_compressed, "_limiter", None)
    if limiter is None:
        limiter = HostRateLimiter(s.requests_per_host_per_second)
        setattr(fetch_html_compressed, "_limiter", limiter)

    if render_js:
        html_text = await _fetch_with_playwright_text(
            normalized,
            settings=s,
            wait_until=wait_until,
            timeout_ms=js_timeout_ms,
            referer=referer,
        )
        return CompressedHTTPResult(
            url=normalized,
            final_url=normalized,
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=html_text.encode("utf-8", errors="replace"),
        )

    return await _fetch_with_httpx_compressed(
        normalized,
        settings=s,
        referer=referer,
        limiter=limiter,
        host=host,
    )


async def _fetch_with_httpx_compressed(
    url: str,
    *,
    settings: HTTPSettings,
    referer: Optional[str],
    limiter: HostRateLimiter,
    host: str,
) -> CompressedHTTPResult:
    """
    Fetch using httpx and return raw bytes as sent over the network.

    Key point
    - We use streaming mode plus aiter_raw() to avoid httpx auto decompression.
      This prevents "double decompress" bugs later in decompress_html_result.

    What this function handles
    - Browser like headers
    - Redirects when enabled
    - Soft rate limiting per host
    - Retries with exponential backoff on transient failures
    - Size limits
    - Content-Type sanity check for HTML
    """
    headers = _default_headers(settings, referer=referer)
    timeout = httpx.Timeout(settings.timeout_seconds)

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=settings.follow_redirects,
        http2=True,
    ) as client:
        last_err: Optional[Exception] = None

        for attempt in range(1, settings.max_retries + 1):
            try:
                # Respect per-host rate limiting
                await limiter.wait(host)

                # Stream the response so we can read raw bytes exactly as delivered
                async with client.stream("GET", url) as r:
                    status = r.status_code

                    # Treat typical transient errors as retryable
                    if status in (429, 500, 502, 503, 504):
                        raise RequestHTTPError(f"HTTP {status}")

                    content_type = r.headers.get("content-type")
                    if not _looks_like_html(content_type):
                        raise RequestHTTPError(f"Content-Type not HTML: {content_type}")

                    # Collect raw bytes without automatic decoding
                    chunks: list[bytes] = []
                    total = 0

                    async for chunk in r.aiter_raw():
                        if not chunk:
                            continue

                        total += len(chunk)

                        # Enforce size cap to protect memory
                        if total > settings.max_response_bytes:
                            remaining = settings.max_response_bytes - (total - len(chunk))
                            if remaining > 0:
                                chunks.append(chunk[:remaining])
                            break

                        chunks.append(chunk)

                    raw = b"".join(chunks)

                    hdrs = {k.lower(): v for k, v in r.headers.items()}
                    final_url = str(r.url)

                    return CompressedHTTPResult(
                        url=url,
                        final_url=_normalize_url(final_url),
                        status_code=status,
                        headers=hdrs,
                        body=raw,
                    )

            except Exception as e:
                last_err = e
                if attempt >= settings.max_retries:
                    break

                # Exponential backoff between attempts
                sleep_s = min(
                    settings.backoff_base_seconds * (2 ** (attempt - 1)),
                    settings.backoff_max_seconds,
                )
                await asyncio.sleep(sleep_s)

        raise RequestHTTPError(f"Could not fetch from {url}. Error: {last_err}")


async def _fetch_with_playwright_text(
    url: str,
    *,
    settings: HTTPSettings,
    wait_until: str,
    timeout_ms: int,
    referer: Optional[str],
) -> str:
    """
    Fetch HTML by rendering the page in a headless browser via Playwright.

    Returns
    - HTML as text using page.content().

    Requirements
    - pip install playwright
    - playwright install
    """
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        raise RequestHTTPError(
            "Playwright is not installed. Install with pip install playwright then run playwright install."
        ) from e

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=settings.user_agent,
            locale="es-CL",
        )
        page = await context.new_page()

        extra_headers = _default_headers(settings, referer=referer)
        await page.set_extra_http_headers(extra_headers)

        try:
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            html = await page.content()
            if not html.strip():
                raise RequestHTTPError("Empty HTML after rendering")
            return html
        finally:
            await context.close()
            await browser.close()


def fetch_html_compressed_sync(
    url: str,
    *,
    settings: HTTPSettings | None = None,
    referer: Optional[str] = None,
    render_js: bool = False,
) -> CompressedHTTPResult:
    """
    Synchronous wrapper around fetch_html_compressed.

    Returns
    - CompressedHTTPResult containing raw bytes.
    """
    return asyncio.run(
        fetch_html_compressed(
            url,
            settings=settings,
            referer=referer,
            render_js=render_js,
        )
    )


async def fetch_html(
    url: str,
    *,
    settings: HTTPSettings | None = None,
    referer: Optional[str] = None,
    render_js: bool = False,
    wait_until: str = "networkidle",
    js_timeout_ms: int = 30_000,
) -> str:
    """
    High level HTML fetch that returns final HTML text.

    Behavior
    - Calls fetch_html_compressed to get bytes plus headers.
    - Decompresses using decompress_html_result.
    - Returns the final HTML as a string.
    """
    compressed = await fetch_html_compressed(
        url,
        settings=settings,
        referer=referer,
        render_js=render_js,
        wait_until=wait_until,
        js_timeout_ms=js_timeout_ms,
    )
    return decompress_html_result(compressed)


def fetch_html_sync(
    url: str,
    *,
    settings: HTTPSettings | None = None,
    referer: Optional[str] = None,
    render_js: bool = False,
) -> str:
    """
    Synchronous wrapper around fetch_html.

    Returns
    - Final HTML as text.
    """
    return asyncio.run(fetch_html(url, settings=settings, referer=referer, render_js=render_js))



"""
fetch_html
-Function: fetch_html
-Description: Main public asynchronous entry point that retrieves the HTML content of a given URL. It supports a fast direct HTTP mode plus an optional JavaScript rendering mode for pages that require a real browser to fully populate the DOM.
-Input: url: String. The target page URL to fetch.
-Output: Returns a string containing the HTML of the page.
-Options:
  -settings: HTTPSettings object or None. Controls timeouts retries redirect handling response size limits per host rate limiting plus the user agent. When None default values are used.
  -referer: String or None. When provided it is sent as the Referer HTTP header.
  -render_js: Boolean. When True the function uses a headless browser via Playwright to render the page plus return the DOM HTML. When False it uses direct HTTP requests via httpx.
  -wait_until: String. Used only when render_js is True. Defines the Playwright navigation wait condition such as load domcontentloaded or networkidle.
  -js_timeout_ms: Integer. Used only when render_js is True. Maximum time in milliseconds to wait for the page to reach the selected wait state.

fetch_html_sync
-Function: fetch_html_sync
-Description: Public synchronous wrapper around fetch_html designed for scripts that do not want to manage asyncio directly. It runs the asynchronous fetch_html function inside a new event loop plus returns the resulting HTML.
-Input: url: String. The target page URL to fetch.
-Output: Returns a string containing the HTML of the page.
-Options:
  -settings: HTTPSettings object or None. Same behavior as in fetch_html.
  -referer: String or None. Same behavior as in fetch_html.
  -render_js: Boolean. Same behavior as in fetch_html. When True it triggers Playwright rendering. When False it uses direct HTTP fetching.


"fetch_html_compressed" and "fetch_html_compressed_sync" do the same but with a comprimed output
"decompress_html_result" decompress comprimed HTML
"""