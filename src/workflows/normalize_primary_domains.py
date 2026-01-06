import os
import sys

# Agregar el directorio raíz del proyecto al path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.logger import setup_logger
from src.DB.platforms_querys import get_all_slugs, manage_primary_domain

# Configuración del Logger
# Se guarda en un archivo específico para este proceso
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'normalize_primary_domains.log'))
logger = setup_logger('normalize_primary_domains', LOG_FILE)

def main():
    logger.info("INICIANDO PROCESO DE NORMALIZACION DE PRIMARY DOMAINS")
    
    # Obtener todos los slugs, incluyendo aquellos que puedan tener datos vacíos
    # para asegurar revisión completa
    slugs = get_all_slugs(include_empty=True)
    logger.info(f"Se encontraron {len(slugs)} documentos para revisar.")
    
    stats = {
        "processed": 0,
        "updated_https": 0,
        "deleted_empty": 0,
        "skipped": 0,
        "errors": 0
    }
    
    for slug in slugs:
        try:
            stats["processed"] += 1
            
            # Obtener primaryDomain actual
            current_domain = manage_primary_domain(slug, action="get")
            
            # Caso 1: Documento sin primaryDomain o es None
            if current_domain is None:
                logger.info(f"SLUG: {slug} - ACTION: SALTADO - DETAILS: No tiene primaryDomain")
                stats["skipped"] += 1
                continue
                
            # Asegurar que sea string por si acaso (aunque la DB debería tener strings o null)
            if not isinstance(current_domain, str):
                logger.warning(f"SLUG: {slug} - ACTION: SALTADO - DETAILS: primaryDomain no es string ({type(current_domain)})")
                stats["skipped"] += 1
                continue
                
            stripped_domain = current_domain.strip()
            
            # Caso 2: String vacío -> Eliminar campo
            if stripped_domain == "":
                manage_primary_domain(slug, action="delete")
                logger.info(f"SLUG: {slug} - ACTION: ELIMINADO - DETAILS: Campo estaba vacío, se eliminó del documento")
                stats["deleted_empty"] += 1
                continue
                
            # Caso 3: Verificar protocolo
            # Si ya tiene http:// o https://, saltar
            if stripped_domain.startswith("http://") or stripped_domain.startswith("https://"):
                logger.info(f"SLUG: {slug} - ACTION: SALTADO - DETAILS: Ya tiene protocolo válido ({stripped_domain})")
                stats["skipped"] += 1
                continue
            
            # Caso 4: Agregar https://
            # Nota: Asumimos que si llegó acá es un dominio "dominio.com" sin protocolo
            new_domain = "https://" + stripped_domain
            manage_primary_domain(slug, action="set", domain=new_domain)
            
            logger.info(f"SLUG: {slug} - ACTION: ACTUALIZADO - DETAILS: '{current_domain}' -> '{new_domain}'")
            stats["updated_https"] += 1
            
        except Exception as e:
            logger.error(f"SLUG: {slug} - ERROR CRITICO: {str(e)}")
            stats["errors"] += 1
            
    # Resumen final
    logger.info("="*50)
    logger.info("RESUMEN DEL PROCESO")
    logger.info(f"Total procesados: {stats['processed']}")
    logger.info(f"Actualizados (agregado https): {stats['updated_https']}")
    logger.info(f"Eliminados (estaban vacíos): {stats['deleted_empty']}")
    logger.info(f"Saltados (sin cambios): {stats['skipped']}")
    logger.info(f"Errores: {stats['errors']}")
    logger.info("="*50)
    print(f"Proceso finalizado. Logs guardados en: {LOG_FILE}")

if __name__ == "__main__":
    main()
