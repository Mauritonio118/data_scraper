
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Agregar directorio raiz al path para imports
current_dir = Path(__file__).resolve().parent
src_path = current_dir.parent.parent
sys.path.append(str(src_path))

from src.DB.platforms_querys import get_slugs_not_inactive, manage_primary_domain, upsert_page_routes
from src.scrapers.favicon_scraper import get_favicon_url

# Configurar Logging
log_dir = os.path.join(src_path, "logs")
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, "favicon_workflow.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def process_favicons():
    logging.info("INICIANDO: Workflow de Extracción de Favicons")
    
    # 1. Obtener slugs activos
    slugs = get_slugs_not_inactive()
    logging.info(f"Se encontraron {len(slugs)} plataformas activas/no-inactivas.")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    total_slugs = len(slugs)

    for i, slug in enumerate(slugs, 1):
        try:
            # 2. Obtener Primary Domain
            primary_domain = manage_primary_domain(slug, action="get")
            
            if not primary_domain:
                logging.warning(f"[{i}/{total_slugs}] SKIP [{slug}]: No tiene primaryDomain.")
                skip_count += 1
                continue
                
            logging.info(f"[{i}/{total_slugs}] PROCESANDO [{slug}]: Dominio -> {primary_domain}")
            
            # 3. Scraper Favicon
            try:
                favicon_url = get_favicon_url(primary_domain)
                logging.info(f"  --> Favicon encontrado: {favicon_url}")
                
                # 4. Guardar en DB
                res = upsert_page_routes(slug, favicon_route=favicon_url)
                
                # Filtrar updatedAt para logs
                res_log = {k: v for k, v in res.items() if k != 'updatedAt'}
                
                if res.get("modified", 0) > 0:
                    logging.info(f"  --> DB Actualizada: {res_log}")
                elif res.get("matched", 0) > 0:
                    logging.info(f"  --> DB Sin cambios (ya existía): {res_log}")
                else:
                    logging.error(f"  --> Error al guardar en DB: {res_log}")
                
                success_count += 1
                
            except Exception as e:
                logging.error(f"  --> FALLO al buscar favicon para {primary_domain}: {e}")
                fail_count += 1
                
        except Exception as e:
            logging.error(f"ERROR CRITICO procesando slug {slug}: {e}")
            fail_count += 1
            
    logging.info("="*30)
    logging.info("RESUMEN FINAL")
    logging.info(f"Total Procesados: {len(slugs)}")
    logging.info(f"Exitosos: {success_count}")
    logging.info(f"Fallidos: {fail_count}")
    logging.info(f"Saltados (Sin Dominio): {skip_count}")
    logging.info("="*30)

if __name__ == "__main__":
    process_favicons()
