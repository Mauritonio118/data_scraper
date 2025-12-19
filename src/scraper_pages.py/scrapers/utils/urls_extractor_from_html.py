from __future__ import annotations

import re
from html import unescape
from typing import List


# This regex extracts values from common URL carrying attributes.
# It captures relative paths like ./regulacion, /ruta, ../algo, also absolute URLs.
_URL_ATTR_RE = re.compile(
    r"""(?isx)
    \b
    (href|src|action|poster|data|formaction)
    \s*=\s*
    (?P<q>["'])
    (?P<val>.*?)
    (?P=q)
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

# srcset may contain multiple URLs separated by commas with descriptors
_SRCSET_RE = re.compile(r"""(?isx)\bsrcset\s*=\s*(?P<q>["'])(?P<val>.*?)(?P=q)""", re.VERBOSE)

# Extract url(...) from inline styles or <style> blocks
_CSS_URL_RE = re.compile(
    r"""(?isx)
    url\(\s*
    (?P<q>["']?)
    (?P<val>[^"')]+)
    (?P=q)
    \s*\)
    """,
    re.VERBOSE,
)

# Meta refresh pattern: content="0; url=./path"
_META_REFRESH_RE = re.compile(r"""(?isx)\burl\s*=\s*(?P<val>[^\s"';>]+)""")


def _clean_value(raw: str) -> str:
    """
    Clean a raw attribute value.

    Steps
    - Strip whitespace
    - HTML unescape entities such as &amp;
    - Remove surrounding whitespace again
    """
    if raw is None:
        return ""
    s = raw.strip()
    if not s:
        return ""
    s = unescape(s)
    return s.strip()


def _is_navigable_link(candidate: str) -> bool:
    """
    Decide if a candidate string is a navigable web link.

    Rejects
    - empty values
    - fragment only references
    - non web schemes such as mailto, tel, javascript
    - data or blob URLs
    """
    if not candidate:
        return False

    low = candidate.lower()

    if candidate.startswith("#"):
        return False

    if low.startswith(("mailto:", "tel:", "sms:", "javascript:", "data:", "blob:", "about:")):
        return False

    return True


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    """
    Remove duplicates while keeping the first occurrence order.
    """
    out: List[str] = []
    seen: set[str] = set()
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def urls_extractor_from_html(html: str) -> List[str]:
    """
    Main function for phase 1: URL discovery.

    Input
    - html: full HTML as a string

    Output
    - list[str] containing every discovered link reference
      Includes absolute URLs plus relative paths such as ./regulacion

    Discovery sources
    - href, src, action, poster, data, formaction
    - srcset entries
    - url(...) inside inline styles plus <style> blocks
    - meta refresh url=...
    - script src attributes

    Notes
    - This function does not resolve relative paths to absolute URLs
    - This function does not filter by domain
    - Those steps belong to later phases
    """
    if not html or not isinstance(html, str):
        return []

    candidates: List[str] = []

    # 1) Extract from common HTML attributes via regex
    for m in _URL_ATTR_RE.finditer(html):
        val = _clean_value(m.group("val") or "")
        if _is_navigable_link(val):
            candidates.append(val)

    # 2) Extract URLs from srcset
    for m in _SRCSET_RE.finditer(html):
        raw_srcset = _clean_value(m.group("val") or "")
        if not raw_srcset:
            continue
        parts = [p.strip() for p in raw_srcset.split(",") if p.strip()]
        for part in parts:
            first_token = part.split()[0].strip()
            first_token = _clean_value(first_token)
            if _is_navigable_link(first_token):
                candidates.append(first_token)

    # 3) Extract url(...) references from CSS
    for m in _CSS_URL_RE.finditer(html):
        val = _clean_value(m.group("val") or "")
        if _is_navigable_link(val):
            candidates.append(val)

    # 4) Extract meta refresh redirect targets
    # This is best effort since meta tags are free form
    # Example: <meta http-equiv="refresh" content="0; url=./regulacion">
    for meta_match in re.finditer(r"""(?is)<meta[^>]+http-equiv\s*=\s*["']refresh["'][^>]*>""", html):
        meta_tag = meta_match.group(0) or ""
        content_match = re.search(r"""(?is)\bcontent\s*=\s*["'](.*?)["']""", meta_tag)
        if not content_match:
            continue
        content_val = _clean_value(content_match.group(1) or "")
        u = _META_REFRESH_RE.search(content_val)
        if u:
            target = _clean_value(u.group("val") or "")
            if _is_navigable_link(target):
                candidates.append(target)

    # Optional BeautifulSoup pass for extra robustness
    # This can catch edge cases missed by regex, without being required
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "lxml")

        for tag in soup.find_all(True):
            # Collect direct attributes
            for attr in ("href", "src", "action", "poster", "data", "formaction"):
                if tag.has_attr(attr):
                    v = tag.get(attr)
                    if isinstance(v, list):
                        for vv in v:
                            vv = _clean_value(str(vv))
                            if _is_navigable_link(vv):
                                candidates.append(vv)
                    else:
                        vv = _clean_value(str(v))
                        if _is_navigable_link(vv):
                            candidates.append(vv)

            # script src
            if tag.name == "script" and tag.has_attr("src"):
                vv = _clean_value(str(tag.get("src") or ""))
                if _is_navigable_link(vv):
                    candidates.append(vv)

            # srcset via parser
            if tag.has_attr("srcset"):
                srcset_val = _clean_value(str(tag.get("srcset") or ""))
                parts = [p.strip() for p in srcset_val.split(",") if p.strip()]
                for part in parts:
                    first_token = _clean_value(part.split()[0].strip())
                    if _is_navigable_link(first_token):
                        candidates.append(first_token)

            # style attribute url(...)
            if tag.has_attr("style"):
                style_val = _clean_value(str(tag.get("style") or ""))
                for mm in _CSS_URL_RE.finditer(style_val):
                    vv = _clean_value(mm.group("val") or "")
                    if _is_navigable_link(vv):
                        candidates.append(vv)

        # <style> blocks
        for st in soup.find_all("style"):
            css = st.get_text(" ", strip=False) or ""
            for mm in _CSS_URL_RE.finditer(css):
                vv = _clean_value(mm.group("val") or "")
                if _is_navigable_link(vv):
                    candidates.append(vv)

    except Exception:
        pass

    return _dedupe_preserve_order(candidates)
