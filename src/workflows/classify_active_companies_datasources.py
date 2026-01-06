import logging
import sys
import os
from typing import List, Optional

# Add the project root to the python path to allow imports from src
# logic similar to other workflows to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.DB.mongo import get_db
from src.analizers.datasource_role_classifier import classify_role_platform_datasources

# Setup logging
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'classify_active_companies_datasources.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def process_active_companies(target_roles: Optional[List[str]] = None):
    """
    Recupera todas las empresas cuyo operational.status NO sea "inactive"
    y clasifica sus datasources.
    """
    logger.info("Starting DataSource Classification for Active Companies.")
    
    if target_roles:
        logger.info(f"Target Roles specified: {target_roles}")
    else:
        logger.info("No specific target roles set. All available roles will be considered.")

    try:
        db = get_db()
        platforms_collection = db["platforms"]
        
        # Query: operational.status != "inactive"
        # Note: This includes cases where operational field doesn't exist, or status is null, etc.
        # If the requirement is strictly "value is not inactive", $ne covers it.
        query = {"operational.status": {"$ne": "inactive"}}
        
        # We only need the slug to call the classifier
        projection = {"slug": 1, "name": 1, "_id": 1}
        
        cursor = platforms_collection.find(query, projection)
        companies_list = list(cursor)
        
        total_companies = len(companies_list)
        logger.info(f"Found {total_companies} platforms to process.")
        
        stats_summary = {
            "processed_companies": 0,
            "total_updates": 0,
            "errors": 0
        }
        
        for i, company in enumerate(companies_list, 1):
            slug = company.get("slug")
            name = company.get("name", "Unknown")
            
            if not slug:
                logger.warning(f"Skipping platform ID {company.get('_id')} - No slug found.")
                continue
            
            logger.info(f"[{i}/{total_companies}] Processing '{name}' (slug: {slug})...")
            
            try:
                # Call the classifier
                result = classify_role_platform_datasources(slug=slug, target_roles=target_roles)
                
                if result.get("error"):
                    logger.warning(f"[{slug}] Result error: {result.get('error')}")
                else:
                    updated = result.get("updated", 0)
                    classified = result.get("classified", 0)
                    total_ds = result.get("processed", 0)
                    
                    if updated > 0:
                        logger.info(f"[{slug}] -> Updated {updated} datasources (Classified: {classified}/{total_ds})")
                        stats_summary["total_updates"] += updated
                    else:
                        logger.info(f"[{slug}] -> No changes (Classified: {classified}/{total_ds})")
                
                stats_summary["processed_companies"] += 1
                
            except Exception as e:
                logger.error(f"Error classifying platform '{slug}': {e}", exc_info=True)
                stats_summary["errors"] += 1
                
        logger.info("Classification process finished.")
        logger.info(f"Summary: {stats_summary}")

    except Exception as e:
        logger.critical(f"Critical error during execution: {e}", exc_info=True)

if __name__ == "__main__":
    # Example usage if run directly
    # Can accept args if needed, but for now defaults to None
    process_active_companies()
