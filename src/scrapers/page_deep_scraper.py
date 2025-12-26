from urllib.parse import urlparse

#BASE DE IMPORTACIONES PARA WORKFLOW
"""
#Import lectura HTML
from src.scrapers.utils.requestHTTP import fetch_html

#import manejo de html
from src.scrapers.utils.html_spliter_head_header_main_footer import html_spliter_head_header_main_footer

#Import manejo de urls desde el HTML
from src.scrapers.utils.urls_extractor_from_html import urls_extractor_from_html  
from src.scrapers.utils.urls_utilities_cleaner import urls_utilities_cleaner
from src.scrapers.utils.urls_format_from_domain import urls_format_from_domain

#import manejo de textos desde el html
from src.scrapers.utils.text_extractor_from_html import text_extractor_from_html
"""

#Import lectura HTML
from src.scrapers.utils.requestHTTP import fetch_html

#import manejo de html
from src.scrapers.utils.html_spliter_head_header_main_footer import html_spliter_head_header_main_footer

#Import manejo de urls desde el HTML
from src.scrapers.utils.urls_extractor_from_html import urls_extractor_from_html  
from src.scrapers.utils.urls_utilities_cleaner import urls_utilities_cleaner
from src.scrapers.utils.urls_format_from_domain import urls_format_from_domain

#import manejo de textos desde el html
from src.scrapers.utils.text_extractor_from_html import text_extractor_from_html



def url_processor_from_html(html, url_base):
    url_list= urls_extractor_from_html(html)
    url_list= urls_utilities_cleaner(url_list)
    url_list= urls_format_from_domain(url_list, url_base)
    return url_list


def flatten_links(links_by_section: dict) -> list[str]:
    out: list[str] = []
    for section in ["head", "header", "main", "footer"]:
        urls = links_by_section.get(section, [])
        if isinstance(urls, list):
            out.extend([u for u in urls if isinstance(u, str)])
    return out


def normalize_url_for_crawl(url: str) -> str:
    """
    Normaliza para deduplicar durante el crawl:
    - trim
    - quita fragmentos
    - quita slash final
    """
    u = (url or "").strip()
    if not u:
        return ""
    u = u.split("#", 1)[0]
    if u.endswith("/") and len(u) > 1:
        u = u[:-1]
    return u


def get_root_domain(url: str) -> str:
    """
    Devuelve un dominio raíz simple.
    Ejemplo: blog.fraccional.cl -> fraccional.cl
    """
    p = urlparse(url)
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def is_same_root_domain(url: str, root_domain: str) -> bool:
    p = urlparse(url)
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host == root_domain or host.endswith("." + root_domain)


async def page_scraper(url_base: str):
    
    #Traer HTML
    html = await fetch_html(url_base)

    #Dividir HTML
    splited_html = html_spliter_head_header_main_footer(html)

    #Nombrar secciones del HTML
    head = splited_html["head"]
    header = splited_html["header"]
    main = splited_html["main"]
    footer = splited_html["footer"]

    #Extraer y pocesar links desde secciones del HTML
    head_links = url_processor_from_html(head, url_base)
    header_links = url_processor_from_html(header, url_base)
    main_links = url_processor_from_html(main, url_base)
    footer_links = url_processor_from_html(footer, url_base)

    #Extraer textos desde secciones del HTML
    head_texts = text_extractor_from_html(head)
    header_texts = text_extractor_from_html(header)
    main_texts = text_extractor_from_html(main)
    footer_texts = text_extractor_from_html(footer)

    #Crear objeto de la pagina
    page_object = {
        "page": url_base,
        "links": {"head":head_links, "header":header_links, "main":main_links, "footer":footer_links },
        "texts": {"head":head_texts, "header":header_texts, "main":main_texts, "footer":footer_texts },
    }

    return page_object


async def page_deep_scraper(url_base: str, max_pages: int = 100):
    start = normalize_url_for_crawl(url_base)
    root_domain = get_root_domain(start)

    to_visit: list[str] = [start]
    visited: set[str] = set()

    pages: dict[str, dict] = {}
    all_internal_links: set[str] = set()

    while to_visit and len(visited) < max_pages:
        current = to_visit.pop(0)
        current = normalize_url_for_crawl(current)

        if not current:
            continue
        if current in visited:
            continue

        visited.add(current)

        try:
            page_obj = await page_scraper(current)
        except Exception as e:
            pages[current] = {
                "page": current,
                "links": {},
                "texts": {},
                "error": {"type": type(e).__name__, "message": str(e)},
            }
            continue

        pages[current] = page_obj

        extracted_links = flatten_links(page_obj.get("links", {}))

        normalized_links = []
        for link in extracted_links:
            nl = normalize_url_for_crawl(link)
            if nl:
                normalized_links.append(nl)

        unique_links = set(normalized_links)

        internal_links = [u for u in unique_links if is_same_root_domain(u, root_domain)]

        for u in internal_links:
            all_internal_links.add(u)
            if u not in visited:
                to_visit.append(u)

    return {
        "startUrl": start,
        "rootDomain": root_domain,
        "pagesScraped": len(pages),
        "allInternalLinks": list(all_internal_links),
        "pages": pages
    }
