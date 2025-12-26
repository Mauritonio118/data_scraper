# data_scraper

Pipeline para pasar de **internet → datos crudos → modelo base en MongoDB → modelo depurado y analizado**.

Incluye:
- **Scrapers** HTTP/Playwright para extraer HTML, links y textos.
- **Utilidades** para limpiar y normalizar URLs y contenido.
- **Módulos de DB** para leer/escribir en MongoDB.
- **Analizers** para clasificar URLs por role y filtrar/depurar la data.
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
  - `role_classifier.py`: **Sistema de clasificación de roles para URLs.**
    - Clase `RoleClassifier` con clasificadores extensibles y personalizables.
    - Roles predefinidos: `official_site`, `official_social_profile`, `official_social_content`, `social_profile`, `social_content`, `store_listing`, `regulator_profile`, `regulator_reference`, `news_site`, `third_party`, `web_utilities`, `documents`, `unclassified`.
    - Funciones de conveniencia: `classify_url()`, `get_available_roles()`, `register_custom_classifier()`.
  - `datasource_role_classifier.py`: **Clasificador de roles para dataSources de compañías.**
    - `classify_company_datasources(slug, target_roles)`: clasifica todos los dataSources de una compañía.
    - `classify_single_datasource(slug, datasource_url)`: clasifica un dataSource específico.
    - `get_datasources_by_role(slug, role)`: obtiene dataSources filtrados por role.
    - `clear_all_company_roles(slug)`: elimina todos los roles de una compañía.
    - `clear_single_datasource_role(slug, datasource_url)`: limpia el role de un dataSource específico.
  - `data_filter.py`: filtros por dominio (redes sociales, app stores, noticias, legal, multimedia, etc.).
  - `model_processor.py`: procesamiento y categorización de links extraídos del scraping.
  - `ANALIZERS_DOCS.ipynb`: **Notebook de documentación y ejemplos** del sistema de clasificación.
- **`workflows/`**
  - `list_to_scrap_to_model_to_DB.py` / `.ipynb`:
    workflow end-to-end desde una lista de empresas hasta el modelo en DB.
  - `companies_list*.csv`: listas de empresas de entrada/salida del proceso.
- Otros:
  - `estructura_recomendada.txt`: notas internas sobre estructura del proyecto.
  - `Ian_test.ipynb`, `Mauro_test.ipynb`: notebooks de pruebas exploratorias.

Raíz del proyecto:
- **`build_venv.py`**: **Script automatizado para crear el entorno virtual `envData`.** Crea el entorno, actualiza pip, instala el proyecto en modo editable (`pip install -e .`) y configura navegadores de Playwright automáticamente.
- **`pyproject.toml`**: Configuración del proyecto para instalación editable.
- `requirements.txt`: dependencias del proyecto.
- `.env` / `.env.example`: variables de entorno.

---

## 2. Requisitos y dependencias

Las dependencias principales están en `requirements.txt`:

- **Jupyter**: `notebook`
- **Control de Versiones para Notebooks**: `nbstripout`
- **HTTP / Parsing**: `httpx`, `httpx[http2]`, `brotli`, `BeautifulSoup4`, `lxml`, `tldextract`
- **Scraping avanzado**: `playwright`
- **DB / Data**: `pymongo`, `pandas`
- **Config**: `python-dotenv`

### Instalación automatizada (recomendado)

Usa el script `build_venv.py` para configurar todo automáticamente:

```bash
python build_venv.py
```

Este script:
1. Crea un entorno virtual `envData` si no existe.
2. Actualiza pip a la última versión.
3. **Instala el proyecto en modo editable** (`pip install -e .`), lo que configura el paquete `src` para que sea accesible desde cualquier lugar.
4. Instala los navegadores de Playwright.
5. **Configura nbstripout** para limpiar automáticamente los outputs de los notebooks antes de un `commit`.

Después de ejecutar el script, solo necesitas:
- Activar el entorno: `envData\Scripts\activate` (Windows) o `source envData/bin/activate` (Linux/Mac)
- Configurar el archivo `.env` con tus credenciales de MongoDB

### Instalación manual

Si prefieres configurar manualmente:

```bash
# Crear entorno virtual
python -m venv envData

# Activar entorno (Windows)
envData\Scripts\activate

# Activar entorno (Linux/macOS)
source envData/bin/activate

# Actualizar pip e instalar proyecto en modo editable
python -m pip install --upgrade pip
pip install -e .

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

## 4. Workflow principal: lista → scraping → modelo → DB

1. Preparar un CSV de empresas dentro de `src/workflows/` (ej: `companies_list.csv`).
2. Revisar/ajustar parámetros en `src/workflows/list_to_scrap_to_model_to_DB.py`
   (columnas de input, colección destino, etc.).
3. Ejecutar el script:

```bash
.venv\Scripts\activate
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

- **Analizadores** (`src/analizers/`):
  - `role_classifier.py`: clasifica URLs por tipo (sitio oficial, redes sociales, reguladores, etc.).
  - `datasource_role_classifier.py`: aplica clasificación masiva a los dataSources de una compañía.
  - `data_filter.py`: filtros por dominio para detectar redes sociales, app stores, noticias, etc.
  - `model_processor.py`: pipeline de procesamiento que categoriza links extraídos.

---

## 6. Cómo contribuir / extender

**Ideas de extensión:**
- Agregar nuevos roles usando `register_custom_classifier()` en `role_classifier.py`.
- Extender los dominios conocidos en los clasificadores existentes.
- Incluir scrapers específicos para ciertas plataformas (ej: marketplaces, directorios).
- Añadir tests unitarios para los helpers de `companies_querys.py` y las funciones de `scrapers/utils`.

**Al hacer cambios:**
- Mantén la misma estructura de carpetas.
- Documenta los nuevos helpers con docstrings y, si aplica, agrega una celda de ejemplo en `ANALIZERS_DOCS.ipynb` o un nuevo notebook en `src/`.

---

## 7. Notas rápidas (cheatsheet)

### Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/Mauritonio118/data_scraper.git
    cd data_scraper
    ```

2.  **Crear y activar entorno virtual** (Recomendado):
    ```bash
    python -m venv envData
    # Windows:
    .\envData\Scripts\activate
    # Linux/Mac:
    source envData/bin/activate
    ```

3.  **Instalar el proyecto en modo editable**:
    Esto instalará todas las dependencias y configurará el paquete `src` para que sea accesible desde cualquier lugar.
    ```bash
    pip install -e .
    ```

4.  **Instalar navegadores de Playwright**:
    ```bash
    playwright install
    ```

### Ejecución

#### Scripts
Ejecutar los workflows como módulos desde la raíz del proyecto:

```bash
# Ejemplo: Correr el workflow principal
python -m src.workflows.list_to_scrap_to_model_to_DB
```

#### Control de Versiones en Notebooks
Este proyecto utiliza `nbstripout` para evitar guardar los outputs y metadatos de los notebooks en Git. Esto mantiene el repositorio limpio y enfocado solo en el código y markdown.
- La configuración es automática al ejecutar `build_venv.py`.
- Al hacer `git commit`, los outputs se limpian automáticamente sin afectar tu archivo local.
 4.2 |