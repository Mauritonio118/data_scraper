# data_scraper

Pipeline para pasar de **internet → datos crudos → modelo base en MongoDB → modelo depurado y analizado**.

Incluye:
- **Scrapers** HTTP/Playwright para extraer HTML, links y textos.
- **Utilidades** para limpiar y normalizar URLs y contenido.
- **Módulos de DB** para leer/escribir en MongoDB.
- **Analizers** para filtrar y depurar la data.
- **Workflows** de extremo a extremo (lista de empresas → scraping → modelo → DB).

---

## 1. Estructura del proyecto

Carpeta `src/`:

- **`scrapers/`**
  - `page_deep_scraper.py`: lógica principal de scraping profundo de páginas.
  - `model_builder.py`: convierte la info scrapeada en el **modelo base** que se guarda en la DB.
  - `utils/`
    - `requestHTTP.py`: `url → html` (peticiones HTTP con httpx / Playwright).
    - `html_spliter_head_header_main_footer.py`: `html → {head, header, main, footer}`.
    - `urls_extractor_from_html.py`: extrae URLs desde HTML.
    - `urls_utilities_cleaner.py`: filtra/limpia URLs (reduce lista a URLs útiles).
    - `urls_format_from_domain.py`: normaliza dominios/URLs.
    - `text_extractor_from_html.py`: extrae texto relevante desde HTML.
- **`DB/`**
  - `mongo.py`: conexión con MongoDB (`get_db`, etc.).
  - `companies_querys.py`: helpers para consultar la colección `companies`
    (slugs, primaryDomain, dataSources, links, textos, roles, kind, etc.).
  - `info_querys.ipynb`: cuaderno demostrativo para probar las queries de `companies_querys.py`.
  - `torpedo_mongo.py`: utilidades extra para operaciones en Mongo.
- **`analizers/`**
  - `data_filter.py`: filtros y reglas para limpiar/seleccionar datos.
  - `model_processor.py`: transformación del modelo base → modelo depurado/listo para análisis.
- **`workflows/`**
  - `list_to_scrap_to_model_to_DB.py` / `.ipynb`:
    workflow end-to-end desde una lista de empresas hasta el modelo en DB.
  - `companies_list*.csv`: listas de empresas de entrada/salida del proceso.
- Otros:
  - `data.txt`: datos de ejemplo / pruebas rápidas.
  - `Ian_test.ipynb`, `Mauro_test.ipynb`: notebooks de pruebas exploratorias.

---

## 2. Requisitos y dependencias

Las dependencias principales están en `requirements.txt`:

- **Jupyter**: `notebook`
- **HTTP / Parsing**: `httpx`, `httpx[http2]`, `brotli`, `BeautifulSoup4`, `lxml`, `tldextract`
- **Scraping avanzado**: `playwright`
- **DB / Data**: `pymongo`, `pandas`
- **Config**: `python-dotenv`

Instalación recomendada:

# Crear entorno virtual
python -m venv envData

# Activar entorno (Windows)
envData\Scripts\activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt

# Instalar navegadores de Playwright
playwright install



