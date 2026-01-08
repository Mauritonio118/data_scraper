import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def get_favicon_url(url: str) -> str:
    """
    Recibe una URL, busca su favicon y retorna la URL completa del mismo.
    
    Estrategia:
    1. Descarga el HTML.
    2. Busca etiquetas <link> dentro del <head>.
    3. Verifica si el atributo rel contiene "icon".
    4. Extrae el href.
    5. Si es una ruta relativa (empieza con / o ..), combínala con el dominio principal.
    6. Si no encuentra nada, asume que es dominio.com/favicon.ico.
    7. Valida que la URL del favicon exista.
    
    Returns:
        str: URL del favicon validada.
        
    Raises:
        Exception: Si no se encuentra un favicon válido o hay error de conexión insalvable.
    """
    
    # Asegurar esquema
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    session = requests.Session()
    # User-Agent basico para evitar bloqueo simple
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    favicon_candidate = None
    
    try:
        # 1. Descarga el HTML
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. Busca etiquetas <link> dentro del <head>
        head = soup.head
        if head:
            links = head.find_all('link')
            for link in links:
                rels = link.get('rel')
                # 3. Verifica si el atributo rel contiene "icon"
                # 'rel' suele ser una lista de strings en bs4 para este tag
                if rels:
                    if isinstance(rels, list):
                        if any('icon' in r.lower() for r in rels):
                            favicon_candidate = link.get('href')
                            break # Encontramos uno, usamos el primero
                    elif isinstance(rels, str):
                        if 'icon' in rels.lower():
                            favicon_candidate = link.get('href')
                            break

        # 4. Extrae el href y 5. Combina si es relativo
        if favicon_candidate:
            favicon_candidate = urljoin(url, favicon_candidate)
            
    except Exception as e:
        print(f"Advertencia: No se pudo parsear el HTML de {url}: {e}")
        # Si falla el parseo, seguimos al fallback
    
    # 6. Si no encuentras nada, asume que es dominio.com/favicon.ico
    if not favicon_candidate:
        parsed_url = urlparse(url)
        # Construir base url limpia (schema + netloc)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        favicon_candidate = urljoin(base_domain, '/favicon.ico')
    
    # 7. Valida por otra llamada http que esa url efectivamente existe
    try:
        # Usamos stream=True para no descargar la imagen entera si es gigante, solo headers y comienzo
        val_response = session.get(favicon_candidate, timeout=10, stream=True)
        
        if val_response.status_code == 200:
            # Opcional: Verificar Content-Type si se quisiera ser más estricto
            # content_type = val_response.headers.get('Content-Type', '')
            # if 'image' in content_type: ...
            return favicon_candidate
        else:
            raise Exception(f"La URL del favicon retorno status {val_response.status_code}")
            
    except Exception as e:
        raise Exception(f"No se pudo validar el favicon en {favicon_candidate}: {e}")

if __name__ == "__main__":
    # Prueba basica si se ejecuta el script
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "https://google.com"
    try:
        print(f"Buscando favicon para: {target}")
        result = get_favicon_url(target)
        print(f"Favicon encontrado: {result}")
    except Exception as e:
        print(f"Error: {e}")
