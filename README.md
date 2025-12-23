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

```bash
# Crear entorno virtual
python -m venv envData

# Activar entorno (Windows)
envData\Scripts\activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt

# Instalar navegadores de Playwright
playwright install
```

---

## 3. Configuración de entorno

- **Variables de entorno**  
  Copia `.env.example` a `.env` y completa los datos de conexión a MongoDB (y cualquier otra credencial necesaria).

- **Conexión a la DB**  
  - El módulo `src/DB/mongo.py` expone funciones como `get_db()` que usan las variables de entorno.  
  - El notebook `src/DB/info_querys.ipynb` muestra ejemplos de uso sobre la colección `companies`.

---

## 4. Flujos típicos de uso

### 4.1. Probar queries sobre la colección `companies`

1. Abrir el notebook `src/DB/info_querys.ipynb`.
2. Ejecutar la celda de conexión (`from mongo import get_db` y selección de `companies`).
3. Usar las secciones:
   - **Slugs**: detectar slugs duplicados o vacíos.
   - **Primary Domain**: revisar `primaryDomain` únicos y repetidos.
   - **DataSources**:
     - URLs únicas / repetidas.
     - Links por secciones (`head`, `header`, `main`, `footer`).
     - Textos extraídos.
     - Campos `role` y `kind` para clasificar URLs.

Este notebook está pensado como **guía de exploración y debugging** de los helpers en `companies_querys.py`.

### 4.2. Ejecución del workflow completo (lista → scraping → modelo → DB)

1. Preparar un CSV de empresas dentro de `src/workflows/` (ej: `companies_list.csv`).
2. Revisar/ajustar parámetros en `src/workflows/list_to_scrap_to_model_to_DB.py`
   (columnas de input, colección destino, etc.).
3. Ejecutar el script:

```bash
envData\Scripts\activate
python src/workflows/list_to_scrap_to_model_to_DB.py
```

4. Verificar los resultados:
   - En la colección `companies` de MongoDB.
   - Usando las queries de `companies_querys.py` o el notebook `info_querys.ipynb`.

---

## 5. Scrapers y utilidades: visión rápida

- **Scraper principal**: `src/scrapers/page_deep_scraper.py`  
  Toma una URL, baja el HTML, separa secciones, extrae links y textos, y genera una estructura que luego consume `model_builder.py`.

- **Model builder**: `src/scrapers/model_builder.py`  
  Convierte la data scrapeada en el **modelo base** que se guarda en `companies` (con `dataSources`, links, textos, etc.).

- **Analizadores**:
  - `data_filter.py`: aplica reglas para reducir ruido (ej: filtrar redes sociales, duplicados, paths irrelevantes).
  - `model_processor.py`: pasos posteriores de limpieza/normalización del modelo.

---

## 6. Cómo contribuir / extender

**Ideas de extensión:**
- Agregar nuevos tipos de `role` y `kind` para clasificar mejor las URLs.
- Incluir scrapers específicos para ciertas plataformas (ej: marketplaces, directorios).
- Añadir tests unitarios para los helpers de `companies_querys.py` y las funciones de `scrapers/utils`.

**Al hacer cambios:**
- Mantén la misma estructura de carpetas.
- Documenta los nuevos helpers con docstrings y, si aplica, agrega una celda de ejemplo en `info_querys.ipynb` o un nuevo notebook en `src/`.

---

## 7. Notas rápidas (cheatsheet)

- **Activar entorno**: `envData\Scripts\activate`
- **Instalar deps**: `pip install -r requirements.txt && playwright install`
- **Probar DB y queries**: `src/DB/info_querys.ipynb`
- **Workflow completo**: `python src/workflows/list_to_scrap_to_model_to_DB.py`