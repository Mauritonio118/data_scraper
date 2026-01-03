import os
import logging
from datetime import datetime
from typing import List, Optional
from src.DB.companies_querys import get_slugs_not_inactive
from src.analizers.datasource_role_classifier import classify_role_company_datasources, clear_all_company_roles

# Configuración de logs
LOG_DIR = os.path.join("logs")
os.makedirs(LOG_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"role_classification_workflow_{TIMESTAMP}.log")

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN DE ROLES
# ==========================================

# Lista de roles a LIMPIAR antes de clasificar
# Si esta lista está vacía, se omite el paso de limpieza.
# "official_site", "official_social_profile", "store_listing", "news_site", "third_party", "documents", "web_utilities", "social_web_utility"
TARGET_ROLES_TO_CLEAR: List[str] = [
    # "official_social_profile", # Ejemplo
    # "social_web_utility"
    "official_social_profile"
]

# Lista de roles a CLASIFICAR
# Si esta lista está vacía, se omite el paso de clasificación.
TARGET_ROLES_TO_CLASSIFY: List[str] = [
    "official_social_profile",
    "social_web_utility"
]

def run_classification_workflow():
    """
    Flujo principal de clasificación de roles para compañías activas.
    Fase 1: Limpieza de roles específicos.
    Fase 2: Clasificación de roles específicos.
    """
    logger.info("INICIANDO FLUJO DE GESTIÓN DE ROLES PARA COMPAÑÍAS ACTIVAS")
    logger.info(f"Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    # 1. Obtener slugs de compañías no inactivas
    slugs = get_slugs_not_inactive()
    total_companies = len(slugs)
    
    logger.info(f"Se encontraron {total_companies} compañías activas (o no inactivas) para procesar.")
    logger.info("="*60 + "\n")

    # ==========================================
    # FASE 1: LIMPIEZA
    # ==========================================
    if TARGET_ROLES_TO_CLEAR:
        logger.info(">>> FASE 1: LIMPIEZA DE ROLES")
        logger.info(f"Roles a limpiar: {TARGET_ROLES_TO_CLEAR}")
        logger.info("-" * 60)

        for i, slug in enumerate(slugs, 1):
            logger.info(f"[{i}/{total_companies}] Limpiando roles para: {slug}")
            
            try:
                result = clear_all_company_roles(slug, target_roles=TARGET_ROLES_TO_CLEAR)
                
                if result.get("error"):
                    logger.error(f"   [ERROR] {result['error']}")
                else:
                    cleared = result.get("cleared", 0)
                    updated = result.get("updated", 0)
                    not_found = result.get("not_found", 0)
                    logger.info(f"   - Roles eliminados: {cleared}")
                    logger.info(f"   - Actualizaciones DB: {updated}")
                    # logger.info(f"   - No coincidentes: {not_found}") # Opcional

            except Exception as e:
                logger.error(f"   [EXCEPTION] {str(e)}")
            
            logger.info("-" * 30) # Separador visual menor entre empresas en limpieza
            
        logger.info("<<< FIN FASE 1: LIMPIEZA DE ROLES\n")
    else:
        logger.info("SALTANDO FASE 1: No hay roles definidos para limpiar.\n")

    # ==========================================
    # FASE 2: CLASIFICACIÓN
    # ==========================================
    if TARGET_ROLES_TO_CLASSIFY:
        logger.info(">>> FASE 2: CLASIFICACIÓN DE ROLES")
        logger.info(f"Roles a clasificar: {TARGET_ROLES_TO_CLASSIFY}")
        logger.info("-" * 60)

        for i, slug in enumerate(slugs, 1):
            logger.info(f"[{i}/{total_companies}] Clasificando roles para: {slug}")
            
            try:
                result = classify_role_company_datasources(slug, target_roles=TARGET_ROLES_TO_CLASSIFY)
                
                if result.get("error"):
                     logger.error(f"   [ERROR] {result['error']}")
                else:
                    processed = result.get("processed", 0)
                    classified = result.get("classified", 0)
                    roles_found = result.get("roles_found", {})
                    
                    logger.info(f"   - URLs procesadas: {processed}")
                    logger.info(f"   - URLs clasificadas: {classified}")
                    
                    if roles_found:
                        roles_msg = ", ".join([f"{r}: {c}" for r, c in roles_found.items()])
                        logger.info(f"   - Detalle: {{ {roles_msg} }}")
                    else:
                        logger.info(f"   - Detalle: Sin nuevos roles.")

            except Exception as e:
                logger.error(f"   [EXCEPTION] {str(e)}")
            
            logger.info("-" * 30) # Separador visual
            
        logger.info("<<< FIN FASE 2: CLASIFICACIÓN DE ROLES\n")
    else:
        logger.info("SALTANDO FASE 2: No hay roles definidos para clasificar.\n")


    logger.info("="*60)
    logger.info("FLUJO FINALIZADO CORRECTAMENTE.")
    logger.info(f"Logs guardados en: {LOG_FILE}")

if __name__ == "__main__":
    run_classification_workflow()
