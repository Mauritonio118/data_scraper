from __future__ import annotations

import re
from typing import List, Set

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


# Tags that never represent user visible text content
_DROP_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "template",
    "iframe",
    "object",
    "embed",
    "meta",
    "link",
    "head",
}


# Whitespace normalization regex
_WS_RE = re.compile(r"\s+")


def _normalize_text(s: str) -> str:
    """
    Normalize extracted text into a clean single line string.

    Steps
    - Strip leading or trailing whitespace
    - Collapse internal whitespace to single spaces
    """
    s = (s or "").strip()
    if not s:
        return ""
    return _WS_RE.sub(" ", s).strip()


def _looks_hidden(tag: Tag) -> bool:
    """
    Best effort detection for nodes that are likely hidden from users.

    Checks
    - hidden attribute
    - aria-hidden="true"
    - inline style hints like display:none or visibility:hidden
    """
    if not isinstance(tag, Tag):
        return False

    if tag.has_attr("hidden"):
        return True

    aria_hidden = (tag.get("aria-hidden") or "").strip().lower()
    if aria_hidden == "true":
        return True

    style = (tag.get("style") or "").lower()
    if "display:none" in style:
        return True
    if "visibility:hidden" in style:
        return True

    return False


def text_extractor_from_html(html: str) -> List[str]:
    """
    Extract user facing text from an HTML string.

    Output
    - List[str] where each entry is a cleaned text chunk
    - Order follows DOM order
    - Duplicates removed

    Strategy
    - Parse HTML into a DOM tree
    - Remove non visible tag types such as script or style
    - Walk the DOM in order
    - Collect text nodes that are not inside hidden containers
    - Normalize whitespace
    """
    if not isinstance(html, str) or not html.strip():
        return []

    soup = BeautifulSoup(html, "lxml")

    # Remove tags that cannot contribute to visible text
    for tname in _DROP_TAGS:
        for node in soup.find_all(tname):
            node.decompose()

    out: List[str] = []
    seen: Set[str] = set()

    # Iterate through all text nodes in DOM order
    for node in soup.descendants:
        if not isinstance(node, NavigableString):
            continue

        text = _normalize_text(str(node))
        if not text:
            continue

        parent = node.parent
        if isinstance(parent, Tag):
            if _looks_hidden(parent):
                continue

            # Walk ancestors to detect hidden containers
            hidden = False
            for anc in parent.parents:
                if isinstance(anc, Tag) and _looks_hidden(anc):
                    hidden = True
                    break
            if hidden:
                continue

        # Deduplicate while preserving order
        if text not in seen:
            seen.add(text)
            out.append(text)

    return out
