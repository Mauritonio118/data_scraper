from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Set
from urllib.parse import urlparse, urldefrag


# -------------------------------------------------------------------
# Configuration that is easy to extend later
# -------------------------------------------------------------------

# Static resources that are rarely useful as navigational targets
# Keep this list conservative, expand over time as you discover new cases
_STATIC_EXT_RE = re.compile(
    r"""\.(css|js|mjs|jpg|jpeg|png|gif|svg|webp|ico|bmp|tiff|woff|woff2|ttf|otf|eot|map|mp4|webm|ogv|ogg|mp3|wav|m4a|avif|pdf|zip|rar|7z)$""",
    re.IGNORECASE,
)

_ANALYTICS_DOMAIN_HINTS = [
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "googlesyndication.com",
    "hotjar.com",
    "segment.io",
    "fullstory.com",
    "mixpanel.com",
    "facebook.com/tr",
    "connect.facebook.net",
    "stats.g.doubleclick.net",
    "framer.com",
    "framer.app",
    "fonts.gstatic.com",
]

_ASSET_PATH_HINTS = [
    "/wp-content/",
    "/static/",
    "/assets/",
    "/images/",
    "/image/",
    "/img/",
    "/fonts/",
    "/media/",
    "/scripts/",
    "/script/",
    "/js/",
    "/css/",
]

_FRAMEWORK_PATH_HINTS = [
    "/_next/",
    "/_next/image",
    "%2f_next%2f",
]

_MANIFEST_HINTS = [
    "manifest",
    ".webmanifest",
    "/api/manifest-gen",
]

# Schemes that are not normal navigational web links
_BAD_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "blob:", "about:", "file:")


@dataclass(frozen=True)
class FilterConfig:
    """
    Filter configuration for the link cleaner.

    This exists because you will likely extend these rules over time.
    """
    analytics_domain_hints: List[str] = None
    asset_path_hints: List[str] = None
    framework_path_hints: List[str] = None
    manifest_hints: List[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "analytics_domain_hints", self.analytics_domain_hints or list(_ANALYTICS_DOMAIN_HINTS))
        object.__setattr__(self, "asset_path_hints", self.asset_path_hints or list(_ASSET_PATH_HINTS))
        object.__setattr__(self, "framework_path_hints", self.framework_path_hints or list(_FRAMEWORK_PATH_HINTS))
        object.__setattr__(self, "manifest_hints", self.manifest_hints or list(_MANIFEST_HINTS))


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _clean_raw(raw: str) -> str:
    """
    Basic normalization for raw strings.

    Steps
    - Ensure input is a string
    - Strip whitespace
    """
    if not raw or not isinstance(raw, str):
        return ""
    return raw.strip()


def _strip_hash(u: str) -> str:
    """
    Remove fragment part (#...) from a link string.
    """
    try:
        base, _frag = urldefrag(u)
        return base
    except Exception:
        return u.split("#", 1)[0]


def _split_base_query(u: str) -> tuple[str, str]:
    """
    Split into (base_without_query, query_without_question_mark).

    If no query exists returns (base, "").
    """
    no_hash = _strip_hash(u)
    if "?" not in no_hash:
        return no_hash, ""
    base, query = no_hash.split("?", 1)
    return base, query


def _dedupe_preserve_order(urls: Iterable[str]) -> List[str]:
    """
    Dedupe while preserving order of first appearance.
    """
    out: List[str] = []
    seen: Set[str] = set()
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _normalize_candidate_keep_relative(raw: str) -> str:
    """
    Normalize a candidate link but keep relative references.

    Accepted outputs
    - Absolute http or https URLs
    - Protocol relative URLs converted to https
    - www.* converted to https
    - Relative paths like ./regulacion, /regulacion, ../algo, regulacion

    Rejected outputs
    - Fragments only like #section
    - Non navigational schemes like mailto:, javascript:, data:
    """
    s = _clean_raw(raw)
    if not s:
        return ""

    low = s.lower()

    if s.startswith("#"):
        return ""

    if low.startswith(_BAD_SCHEMES):
        return ""

    if s.startswith("//"):
        return "https:" + s

    if low.startswith("www."):
        return "https://" + s

    return s


def _looks_like_absolute_web_url(u: str) -> bool:
    """
    Returns True for absolute http or https URLs.
    """
    try:
        p = urlparse(u)
    except Exception:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


# -------------------------------------------------------------------
# Utility filtering logic
# -------------------------------------------------------------------

def is_web_utility(raw_url: str, *, config: FilterConfig | None = None) -> bool:
    """
    Decide if a link is likely a web utility or a non navigational resource.

    True means discard.
    False means keep.

    This function must accept both absolute URLs plus relative paths.
    """
    cfg = config or FilterConfig()

    u = _clean_raw(raw_url)
    if not u:
        return True

    low = u.lower()

    # Common garbage placeholders
    if u in {"/", "./", "#"}:
        return True
    if low == "[object object]":
        return True

    # Inline images or embedded resources
    if low.startswith("data:image"):
        return True

    # Common avatar CDN links
    if "lh3.googleusercontent.com" in low:
        return True

    # Maps deep links that are usually not a relevant navigation target
    if "google.com/maps" in low:
        if "/contrib/" in low or "/reviews" in low:
            return True

    # Framework internal paths
    for hint in cfg.framework_path_hints:
        if hint in low:
            return True

    # PWA manifest resources
    for hint in cfg.manifest_hints:
        if hint in low:
            return True

    # Extension checks should ignore query and fragment
    base, _query = _split_base_query(low)
    if _STATIC_EXT_RE.search(base):
        return True

    # Analytics and tracking
    for d in cfg.analytics_domain_hints:
        if d in low:
            return True

    # Asset path hints
    for p in cfg.asset_path_hints:
        if p in low:
            return True

    return False


def is_filtered_variant(raw_url: str, base_set: Set[str]) -> bool:
    """
    Drop query variants if the base form already exists.

    Works for absolute URLs and for relative paths.

    Example
    - base_set contains /about
    - candidate is /about?utm_source=x
    This returns True.
    """
    u = _clean_raw(raw_url)
    if not u:
        return False

    base, query = _split_base_query(u)
    if not query:
        return False

    return base in base_set


# -------------------------------------------------------------------
# Main function for phase 2: keep navigational links including relative paths
# -------------------------------------------------------------------

def urls_utilities_cleaner(
    candidates: List[str],
    *,
    config: FilterConfig | None = None,
) -> List[str]:
    """
    Filter a list of link candidates to keep navigational links.

    Requirements covered
    - Keeps external links
    - Keeps subdomains and related domains automatically because no domain restriction is applied
    - Keeps internal relative paths like ./regulacion and /regulacion
    - Removes web utilities, internal framework assets, static resources, trackers
    - Removes query variants when a base entry exists

    Input
    - candidates: list of strings extracted from HTML

    Output
    - cleaned list of strings, order preserved, duplicates removed

    Notes
    - This function does not resolve relative paths to absolute URLs
      That belongs to your future formatting step
    """
    cfg = config or FilterConfig()

    # Normalize while keeping relative paths
    normalized: List[str] = []
    for raw in candidates or []:
        u = _normalize_candidate_keep_relative(raw)
        if not u:
            continue
        normalized.append(u)

    # Build base set from entries without query
    base_set: Set[str] = set()
    for u in normalized:
        base, query = _split_base_query(u)
        if not query:
            base_set.add(base)

    kept: List[str] = []
    for u in normalized:
        if is_web_utility(u, config=cfg):
            continue
        if is_filtered_variant(u, base_set):
            continue

        # Optional small cleanup: drop empty absolute URLs that fail parsing
        # Keep relative strings even if urlparse is weird
        if _looks_like_absolute_web_url(u) or not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*:", u):
            kept.append(u)

    return _dedupe_preserve_order(kept)
