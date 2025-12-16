#Import lectura HTML
from utils.requestHTTP import fetch_html

#import manejo de html
from utils.html_spliter_head_header_main_footer import html_spliter_head_header_main_footer

#Import manejo de urls desde el HTML
from utils.urls_extractor_from_html import urls_extractor_from_html  
from utils.urls_utilities_cleaner import urls_utilities_cleaner
from utils.urls_format_from_domain import urls_format_from_domain

#import manejo de textos desde el html
from utils.text_extractor_from_html import text_extractor_from_html


def url_processor_from_html(html, url_base):
    url_list= urls_extractor_from_html(html)
    url_list= urls_utilities_cleaner(url_list)
    url_list= urls_format_from_domain(url_list, url_base)
    return url_list


async def page_analyzer(url_base: str):
    
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


