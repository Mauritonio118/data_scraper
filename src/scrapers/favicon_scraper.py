import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys

def parse_sizes_attribute(sizes_attr: str) -> int:
    """
    Parsea el atributo 'sizes' (ej: '192x192', '32x32', 'any') y retorna un puntaje numérico (ancho * alto).
    Si hay multiple tamaños (ej: '32x32 48x48'), toma el más grande.
    'any' recibe un puntaje muy alto (SVG).
    Retorna 0 si no puede parsear.
    """
    if not sizes_attr:
        return 0
    
    sizes_attr = sizes_attr.lower().strip()
    
    if sizes_attr == 'any':
        return 10_000_000 # Definición vectorial / "infinita"
        
    try:
        # El estándar permite múltiples tamaños separados por espacio
        parts = sizes_attr.split()
        max_area = 0
        
        for part in parts:
            if 'x' in part:
                w_str, h_str = part.split('x')
                w = int(w_str)
                h = int(h_str)
                area = w * h
                if area > max_area:
                    max_area = area
        return max_area
    except:
        return 0

def get_favicon_url(url: str) -> str:
    """
    Recibe una URL, busca todos los candidatos a favicon, los ordena por calidad/tamaño
    y retorna la URL del mejor candidato válido.
    
    Estrategia mejorada:
    1. Descarga el HTML.
    2. Recolecta todos los <link> relevantes (rel="icon", "apple-touch-icon", etc.).
    3. Asigna un puntaje a cada candidato basado en el atributo 'sizes' o heurísticas (apple icon > icon genérico).
    4. Agrega un fallback por defecto (/favicon.ico) al final de la lista con puntaje bajo.
    5. Ordena candidatos de mayor a menor puntaje.
    6. Itera validando (request HTTP) hasta encontrar el primero que responda OK.
    
    Returns:
        str: URL del favicon validada.
        
    Raises:
        Exception: Si no se encuentra ningún favicon válido tras probar todos los candidatos.
    """
    
    # Asegurar esquema
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    session = requests.Session()
    # User-Agent para parecer navegador real
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    candidates = [] # Lista de dicts: {'href': str, 'score': int, 'source': str}
    
    try:
        # 1. Descarga el HTML
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. Busca etiquetas <link> y extraer candidatos
        head = soup.head
        if head:
            links = head.find_all('link')
            for link in links:
                rels = link.get('rel')
                href = link.get('href')
                
                if not href:
                    continue
                    
                # Normalizar rels a lista lowercase
                if isinstance(rels, str):
                    rels = [rels]
                if not rels:
                    continue
                rels_lower = [r.lower() for r in rels]
                
                # Verificar si es icon
                is_icon = any('icon' in r for r in rels_lower)
                if not is_icon:
                    continue
                    
                # 3. Calcular Puntaje
                sizes_attr = link.get('sizes')
                score = parse_sizes_attribute(sizes_attr)
                
                # Heurísticas si no hay 'sizes'
                if score == 0:
                    if 'apple-touch-icon' in rels_lower:
                        # Apple touch icons suelen ser de buena calidad (ej: 180x180)
                        score = 180 * 180 
                    elif 'shortcut' in rels_lower or 'icon' in rels_lower:
                        # Icono estándar sin size declarado, asumimos bajo (ej: 16x16 o 32x32)
                        score = 32 * 32
                
                # Verificar extensión para bonus (svg) aunque 'sizes=any' ya lo cubre
                if '.svg' in href.lower():
                    score = max(score, 5000 * 5000) # Forzar prioridad alta si es SVG explícito

                candidates.append({
                    'href': href,
                    'score': score,
                    'source': f"html tag (rel={rels}, sizes={sizes_attr})"
                })

    except Exception as e:
        print(f"Advertencia: No se pudo parsear el HTML de {url}: {e}")
        # Continuamos para agregar el fallback
    
    # 4. Fallback default
    # Se agrega con score bajo para que sea la última opción
    candidates.append({
        'href': '/favicon.ico',
        'score': 1, # El puntaje más bajo
        'source': 'fallback default'
    })
    
    # Eliminar duplicados de URLs absolutas (para no chequear lo mismo dos veces)
    # Primero resolvemos URLs
    unique_candidates = []
    seen_urls = set()
    
    for cand in candidates:
        full_url = urljoin(url, cand['href'])
        if full_url not in seen_urls:
            cand['full_url'] = full_url
            seen_urls.add(full_url)
            unique_candidates.append(cand)
            
    # 5. Ordenar por score descendente
    unique_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Debug opcional
    # print(f"Candidatos para {url}:")
    # for c in unique_candidates:
    #     print(f" - {c['score']}: {c['full_url']} ({c['source']})")

    # 6. Validar uno por uno
    last_error = None
    
    for candidate in unique_candidates:
        cand_url = candidate['full_url']
        try:
            # Usamos stream=True para validar headers sin bajar todo el contenido
            val_response = session.get(cand_url, timeout=10, stream=True)
            
            if val_response.status_code == 200:
                # Validar Content-Type
                ctype = val_response.headers.get('Content-Type', '').lower()
                # Permitir imagenes y octet-stream (comun en .ico mal configurados)
                if 'image' in ctype or 'octet-stream' in ctype:
                    return cand_url
                else:
                    # En algun caso raro devuelven HTML 200 OK para 404
                    pass
            
        except Exception as e:
            last_error = e
            continue
            
    # Si llegamos aca, ninguno funcionó
    raise Exception(f"No se pudo encontrar un favicon válido. Último error: {last_error}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://google.com"
    try:
        print(f"Buscando favicon para: {target}")
        result = get_favicon_url(target)
        print(f"Favicon encontrado: {result}")
    except Exception as e:
        print(f"Error: {e}")
