Scraper(internet -> Data -> Modelo base)
DB(Lectura y escritura de bases de datos)
analizers(Modelo base -> Analisis -> Modelo Depurado)


page_deep_scraper:
- page_scraper: url -> (links, text)_dictionary
- 

model_builder:


utils
- requestHTTP.py: link -> html
- html_spliter: html -> content_dictionary
- urls_extractor: str -> url
- urls_utilities_cleaner: urls -> urls_utiles (reduce list)
- urls_format: url -> url_limpio
- text_extractor: str -> str_info_relevante

- data filter: list of links -> list of lists of links


DEPENDENCIAS:
pip install notebook
pip install httpx
pip install httpx[http2]
pip install brotli
pip install BeautifulSoup4
pip install lxml
pip install tldextract
pip install playwright
playwright install          #No olvidar


ENTORNO PYTHON:
Crear: cmd -> python -m venv envData
Activar: cmd-> envData\Scripts\activate
Instalar dependencias: cmd -> python -m pip install --upgrade pip
                           -> pip install -r requirements.txt
                           -> playwright install
Desactivar: cmd -> deactivate


