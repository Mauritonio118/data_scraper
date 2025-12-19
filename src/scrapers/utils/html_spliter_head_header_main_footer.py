from __future__ import annotations

from typing import Dict
from bs4 import BeautifulSoup


def html_spliter_head_header_main_footer(html: str) -> Dict[str, str]:
    """
    Split a full HTML document into four logical sections.

    Output keys
    - head: content inside <head>
    - header: visible header section inside <body>
    - main: main visible content excluding header and footer
    - footer: visible footer section inside <body>

    Design goals
    - Do not confuse <head> with <header>
    - Prefer semantic tags
    - Use id and class hints as fallback
    - Preserve raw HTML for later processing
    """
    if not isinstance(html, str) or not html.strip():
        return {
            "head": "",
            "header": "",
            "main": "",
            "footer": "",
        }

    soup = BeautifulSoup(html, "lxml")

    # -------------------------------------------------
    # HEAD
    # -------------------------------------------------
    head_html = str(soup.head) if soup.head else ""

    # -------------------------------------------------
    # BODY
    # -------------------------------------------------
    body = soup.body if soup.body else soup

    def pick_by_hint(hints: tuple[str, ...]):
        """
        Find the first element whose id or class contains one of the hints.
        """
        for el in body.find_all(True):
            el_id = (el.get("id") or "").lower()
            el_cls = " ".join(el.get("class") or []).lower()
            for h in hints:
                if h in el_id or h in el_cls:
                    return el
        return None

    # -------------------------------------------------
    # HEADER (visible top section)
    # -------------------------------------------------
    header_el = (
        body.find("header")
        or body.find(attrs={"role": "banner"})
        or pick_by_hint(("header", "site-header", "topbar", "navbar", "nav-bar"))
    )

    header_html = str(header_el) if header_el else ""

    # -------------------------------------------------
    # FOOTER (visible bottom section)
    # -------------------------------------------------
    footer_el = (
        body.find("footer")
        or body.find(attrs={"role": "contentinfo"})
        or pick_by_hint(("footer", "site-footer", "page-footer"))
    )

    footer_html = str(footer_el) if footer_el else ""

    # -------------------------------------------------
    # MAIN
    # -------------------------------------------------
    main_el = body.find("main")

    if main_el:
        main_html = str(main_el)
    else:
        # Clone body to safely remove header and footer
        body_clone = BeautifulSoup(str(body), "lxml")
        body_root = body_clone.body if body_clone.body else body_clone

        if header_el:
            cloned_header = body_root.find(header_el.name, id=header_el.get("id"))
            if not cloned_header:
                cloned_header = body_root.find("header")
            if cloned_header:
                cloned_header.decompose()

        if footer_el:
            cloned_footer = body_root.find(footer_el.name, id=footer_el.get("id"))
            if not cloned_footer:
                cloned_footer = body_root.find("footer")
            if cloned_footer:
                cloned_footer.decompose()

        main_html = "".join(str(x) for x in body_root.contents).strip()

    return {
        "head": head_html,
        "header": header_html,
        "main": main_html,
        "footer": footer_html,
    }
