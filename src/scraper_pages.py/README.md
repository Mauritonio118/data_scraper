page_deep_scraper:
- page_scraper: url -> (links, text)_dictionary
- 

model_builder:


utils:
- requestHTTP.py: link -> html
- html_spliter: html -> content_dictionary
- urls_extractor: str -> url
- urls_utilities_cleaner: urls -> urls_utiles (reduce list)
- urls_format: url -> url_limpio
- text_extractor: str -> str_info_relevante

- data filter:
is_in_root_domain(url, url) -> Bool


DEPENDENCIAS:
pip install httpx
pip install playwright
playwright install
pip install httpx[http2]
pip install brotli
pip install BeautifulSoup4
pip install lxml


ACTIVAR ENTORNO:
cmd-> venv\Scripts\activate 