from __future__ import annotations

import re
from typing import List, Set
from urllib.parse import urlparse, urlunparse, ParseResult


# Schemes that are not normal web navigation targets
_NON_WEB_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+\-.]*:")


def _trim_safe(v: str) -> str:
    """
    Safe trim for inputs that should be strings.

    Returns an empty string for None or non string values.
    """
    return v.strip() if isinstance(v, str) else ""


def _remove_trailing_slashes(u: str) -> str:
    """
    Remove one or more trailing slashes.

    Example
    - "https://a.com/x/" becomes "https://a.com/x"
    - "dominio.com///" becomes "dominio.com"
    """
    return re.sub(r"/+$", "", u)


def _ensure_protocol(u: str) -> str:
    """
    Ensure the string starts with https or http.

    If it already starts with http or https it is returned as is.
    Otherwise it is prefixed with https.
    """
    if re.match(r"^https?://", u, flags=re.IGNORECASE):
        return u
    return "https://" + u


def _is_relative(u: str) -> bool:
    """
    Detect relative references used in HTML links.

    Examples considered relative
    - "/ruta"
    - "./ruta"
    """
    return u.startswith("/") or u.startswith("./")


def _complete_relative(u: str, base_domain: str) -> str:
    """
    Convert a relative path into a domain based URL without protocol.

    Examples
    - base_domain="dominio.com" and u="/a" becomes "dominio.com/a"
    - base_domain="dominio.com" and u="./a" becomes "dominio.com/a"
    """
    if not base_domain:
        return u

    if u.startswith("/"):
        return f"{base_domain}{u}"

    if u.startswith("./"):
        rest = u[2:]
        if not rest.startswith("/"):
            rest = "/" + rest
        return f"{base_domain}{rest}"

    return u


def _extract_base_domain(main_url: str) -> str:
    """
    Extract the host without leading www from a main page URL string.

    Expected outputs
    - "https://www.dominio.com/ruta" -> "dominio.com"
    - "http://www.dominio.com/" -> "dominio.com"
    - "dominio.com" -> "dominio.com"
    - "www.dominio.com" -> "dominio.com"
    - "//www.dominio.com/ruta" -> "dominio.com"
    - "https://algo.dominio.otroalgo.com/ruta" -> "algo.dominio.otroalgo.com"

    Notes
    - This function only removes a leading www. from the host.
    - It does not attempt public suffix parsing.
      It follows your requirement: take the host as it appears then remove www.
    """
    raw = _trim_safe(main_url)
    if not raw:
        return ""

    # If someone passes a relative path here, do not return a base domain
    if raw.startswith("/") or raw.startswith("./"):
        return ""

    normalized = raw
    if normalized.startswith("//"):
        normalized = "https:" + normalized

    try:
        has_proto = re.match(r"^https?://", normalized, flags=re.IGNORECASE) is not None
        parsed = urlparse(normalized if has_proto else "https://" + normalized)
        host = (parsed.netloc or "").strip()
        host = re.sub(r"^www\.", "", host, flags=re.IGNORECASE)
        return host
    except Exception:
        # Fallback parsing when urlparse cannot handle the string
        cleaned = re.sub(r"^https?://", "", normalized, flags=re.IGNORECASE)
        cleaned = re.sub(r"^//", "", cleaned)
        cleaned = re.sub(r"^www\.", "", cleaned, flags=re.IGNORECASE)

        # Stop at first separator that begins path query or fragment
        stop_positions = [pos for pos in (cleaned.find("/"), cleaned.find("?"), cleaned.find("#")) if pos != -1]
        stop = min(stop_positions) if stop_positions else -1
        return (cleaned if stop == -1 else cleaned[:stop]).strip()


def _strip_www_only_in_host(raw_url: str) -> str:
    """
    Remove www. only from the host portion of a URL like string.

    Cases handled
    - "https://www.a.com/x" -> "https://a.com/x"
    - "http://www.a.com" -> "http://a.com"
    - "//www.a.com/x" -> "//a.com/x"
    - "www.a.com/x" -> "a.com/x"
    - "a.com/x" stays unchanged

    Important
    - If the input has a non http scheme like mailto:, it is returned unchanged.
    """
    u = _trim_safe(raw_url)
    if not u:
        return ""

    # If it looks like a scheme but not http(s), do not modify
    if _NON_WEB_SCHEME_RE.match(u) and not re.match(r"^https?://", u, flags=re.IGNORECASE):
        return raw_url

    had_protocol_relative = u.startswith("//")
    if had_protocol_relative:
        u_work = "https:" + u
    else:
        u_work = u

    try:
        has_proto = re.match(r"^https?://", u_work, flags=re.IGNORECASE) is not None
        parsed = urlparse(u_work if has_proto else "https://" + u_work)

        host = re.sub(r"^www\.", "", parsed.netloc, flags=re.IGNORECASE)

        rebuilt: str
        if re.match(r"^https?://", u, flags=re.IGNORECASE):
            rebuilt = urlunparse(
                ParseResult(
                    scheme=parsed.scheme,
                    netloc=host,
                    path=parsed.path,
                    params=parsed.params,
                    query=parsed.query,
                    fragment=parsed.fragment,
                )
            )
            return rebuilt

        if had_protocol_relative:
            return "//" + host + parsed.path + (("?" + parsed.query) if parsed.query else "") + (("#" + parsed.fragment) if parsed.fragment else "")

        # No scheme originally
        return host + parsed.path + (("?" + parsed.query) if parsed.query else "") + (("#" + parsed.fragment) if parsed.fragment else "")

    except Exception:
        # Strong fallback: remove scheme and leading // then remove www. at the start
        no_proto = re.sub(r"^https?://", "", u, flags=re.IGNORECASE)
        no_proto = re.sub(r"^//", "", no_proto)
        return re.sub(r"^www\.", "", no_proto, flags=re.IGNORECASE)


def urls_format_from_domain(urls: List[str], page_url: str) -> List[str]:
    """
    Format a list of URL strings using the domain extracted from page_url.

    Required transformations
    - Extract base domain from page_url as host without leading www.
    - Remove www. from every link but only from the host part
    - If the last character is "/" remove it
    - For internal routes like "./ruta" or "/ruta/a" prefix the extracted domain
      Output for those is domain.com/ruta or domain.com/ruta/a
    - Add https:// to every link that does not start with http:// or https://
    - Deduplicate the final outputs

    Notes
    - This function keeps the full host for external URLs including subdomains.
      It only removes a leading www.
    """
    base_domain = _extract_base_domain(page_url)

    out: List[str] = []
    seen: Set[str] = set()

    for raw in urls or []:
        u = _trim_safe(raw)
        if not u:
            continue

        # Leave non web schemes untouched
        if _NON_WEB_SCHEME_RE.match(u) and not re.match(r"^https?://", u, flags=re.IGNORECASE):
            key = u
            if key not in seen:
                seen.add(key)
                out.append(u)
            continue

        # Complete internal routes using the extracted domain
        if _is_relative(u):
            u = _complete_relative(u, base_domain)

        # Remove www only from the host part
        u = _strip_www_only_in_host(u)

        # Remove trailing slashes
        u = _remove_trailing_slashes(u)

        # Ensure protocol for web URLs
        u = _ensure_protocol(u)

        # Deduplicate
        if u and u not in seen:
            seen.add(u)
            out.append(u)

    return out
