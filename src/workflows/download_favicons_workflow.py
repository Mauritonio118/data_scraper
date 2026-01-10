import logging
import sys
import os
import requests
import io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

# Agregar directorio raiz al path para imports
current_dir = Path(__file__).resolve().parent
src_path = current_dir.parent.parent
sys.path.append(str(src_path))

from src.DB.platforms_querys import get_slugs_not_inactive, get_page_routes

# Configurar Logging
log_dir = os.path.join(src_path, "logs")
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, "download_favicons_workflow.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def is_svg_content(content: bytes, headers: dict) -> bool:
    """Detecta si el contenido es SVG analizando headers o bytes."""
    content_type = headers.get('Content-Type', '').lower()
    if 'image/svg' in content_type or 'xml' in content_type:
        # Checkeo básico de bytes
        if b'<svg' in content[:2000].lower():
            return True
    
    # Fallback: mirar los primeros bytes aunque el header mienta
    if b'<svg' in content[:1000].lower().strip():
        return True
        
    return False

def download_and_convert_favicons():
    logging.info("INICIANDO: Workflow de Descarga y Normalización de Favicons (PNG)")
    logging.info("MODO: Híbrido (Pillow para raster, Playwright para SVG)")
    
    # 1. Obtener slugs activos
    slugs = get_slugs_not_inactive()
    logging.info(f"Se encontraron {len(slugs)} plataformas activas/no-inactivas.")
    
    # Crear directorio de destino
    favicons_dir = os.path.join(src_path, "favicons")
    os.makedirs(favicons_dir, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    total_slugs = len(slugs)
    
    headers_http = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Iniciamos Playwright una sola vez para reutilizar el navegador en los casos de SVG
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Contexto minimalista
        context = browser.new_context(viewport={'width': 500, 'height': 500}) 
        page = context.new_page()

        for i, slug in enumerate(slugs, 1):
            try:
                # 2. Obtener Page Routes
                page_routes = get_page_routes(slug)
                favicon_url = None
                if page_routes and isinstance(page_routes, dict):
                    favicon_url = page_routes.get('faviconRoute')
                
                if not favicon_url:
                    logging.warning(f"[{i}/{total_slugs}] SKIP [{slug}]: No tiene faviconRoute en DB.")
                    skip_count += 1
                    continue
                
                logging.info(f"[{i}/{total_slugs}] PROCESANDO [{slug}]: {favicon_url}")
                
                # 3. Descargar Imagen (Bytes)
                try:
                    response = requests.get(favicon_url, headers=headers_http, timeout=20)
                except Exception as e:
                    logging.error(f"  --> FALLO de conexión para {slug}: {e}")
                    fail_count += 1
                    continue
                    
                if response.status_code != 200:
                    logging.error(f"  --> HTTP Error {response.status_code} al descargar: {favicon_url}")
                    fail_count += 1
                    continue
                
                content_bytes = response.content
                filepath = os.path.join(favicons_dir, f"{slug}.png")
                
                # 4. Determinar tipo y convertir
                if is_svg_content(content_bytes, response.headers):
                    logging.info(f"  --> Detectado formato SVG. Usando Playwright para renderizar...")
                    try:
                        # Convertir bytes a string para inyectar
                        # Intentar utf-8, fallback a latin1 o ignorar errores
                        try:
                            svg_text = content_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            svg_text = content_bytes.decode('latin-1')
                            
                        # Limpiar posible declaración XML que moleste si se inserta in-body (aunque set_content maneja full html)
                        # Estrategia: Cargar como contenido HTML directo
                        html_content = f'''
                        <html>
                            <body style="margin:0; padding:0; background-color: transparent;">
                                {svg_text}
                            </body>
                        </html>
                        '''
                        page.set_content(html_content)
                        
                        # Localizar el elemento SVG
                        # Esperamos brevemente a que esté presente
                        try:
                            locator = page.locator('svg').first
                            locator.wait_for(timeout=3000)
                            
                            # Screenshot con fondo transparente
                            locator.screenshot(path=filepath, type="png", omit_background=True)
                            
                            if os.path.exists(filepath):
                                logging.info(f"  --> OK: SVG -> PNG guardado.")
                                success_count += 1
                            else:
                                logging.error(f"  --> Error: Playwright no generó el archivo.")
                                fail_count += 1
                                
                        except Exception as e:
                            logging.error(f"  --> Error encontrando/renderizando elemento SVG: {e}")
                            # Fallback: screenshot de toda la página (recortada?) No, mejor fallar y loguear.
                            # A veces el svg no tiene tag svg explicito en root? (raro)
                            fail_count += 1
                            
                    except Exception as e:
                         logging.error(f"  --> Error crítico Playwright SVG para {slug}: {e}")
                         fail_count += 1
                else:
                    # Asumimos Raster (Pillow)
                    try:
                        image_data = io.BytesIO(content_bytes)
                        img = Image.open(image_data)
                        
                        # Manejar ICO con multiples tamaños -> tomar el mas grande? 
                        # Image.open lee el más grande por defecto o el primero. Pillow suele manejarlo bien.
                        # Para ICOs con múltiples imágenes, `img` es la layer seleccionada.
                        
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                            
                        img.save(filepath, format='PNG', optimize=True)
                        logging.info(f"  --> OK: Raster ({img.format}) -> PNG procesado con Pillow.")
                        success_count += 1
                        
                    except Exception as e:
                        logging.error(f"  --> Error Pillow (Imagen inválida o no soportada): {e}")
                        fail_count += 1

            except Exception as e:
                logging.error(f"ERROR Goblal procesando {slug}: {e}")
                fail_count += 1
                
        browser.close()
            
    logging.info("="*30)
    logging.info("RESUMEN FINAL")
    logging.info(f"Total Procesados: {len(slugs)}")
    logging.info(f"Exitosos (PNG): {success_count}")
    logging.info(f"Fallidos: {fail_count}")
    logging.info(f"Saltados: {skip_count}")
    logging.info("="*30)
    logging.info(f"Directorio salida: {favicons_dir}")

if __name__ == "__main__":
    download_and_convert_favicons()
