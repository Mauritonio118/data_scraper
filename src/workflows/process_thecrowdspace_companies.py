# python src/workflows/process_thecrowdspace_companies.py
import csv
import sys
import os
import logging
from typing import Dict, Any

# Add the project root to the python path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

# Setup logging to file
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'process_thecrowdspace_companies.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    from src.DB.platforms_querys import platforms
    from src.scrapers.thecrowdspace_profile_scraper import thecrowdspace_profile_scraper
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    logger.error("Please ensure you are running this script from the project root or that the python path is set correctly.")
    sys.exit(1)

def process_platforms():
    csv_path = os.path.join(current_dir, 'companies_list.csv')
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        return

    logger.info(f"Starting execution. Reading CSV: {csv_path}")

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                slug = row.get("Slug")
                link_thecrowdspace = row.get("Link_Thecrowdspace")
                platform_name = row.get("Nombre", "Unknown")

                # Validate essential fields
                if not slug or not slug.strip():
                    # Skipping rows without slug is expected if data is missing, but helpful to log trace for debugging
                    logger.debug(f"Skipping row with missing Slug. ID: {row.get('ID')}")
                    continue
                
                if not link_thecrowdspace or not link_thecrowdspace.strip():
                    logger.debug(f"Skipping company '{platform_name}' ({slug}) - No Link_Thecrowdspace provided.")
                    continue

                slug = slug.strip()
                link_thecrowdspace = link_thecrowdspace.strip()

                logger.info(f"Processing company: {platform_name} (Slug: {slug})")

                # 1. Validate existence in MongoDB
                platform_doc = platforms.find_one({"slug": slug})
                
                if not platform_doc:
                    logger.warning(f"Platform with slug '{slug}' not found in MongoDB. Skipping.")
                    continue

                logger.info(f"Platform '{slug}' found in DB. ID: {platform_doc.get('_id')}")

                # 2. Construct complete URL
                # Ensure we don't double protocol if it's already there (though instruction said "agregarle un https://")
                if link_thecrowdspace.startswith("http://") or link_thecrowdspace.startswith("https://"):
                    full_url = link_thecrowdspace
                else:
                    full_url = f"https://{link_thecrowdspace}"
                
                logger.info(f"Scraping URL: {full_url}")

                # 3. Scrape the profile
                try:
                    scraped_data = thecrowdspace_profile_scraper(url=full_url)
                    
                    if not scraped_data:
                        logger.error(f"Scraper returned empty data for {full_url}. Skipping update.")
                        continue
                        
                except Exception as e:
                    logger.error(f"Exception occurred while scraping {full_url}: {e}", exc_info=True)
                    continue

                # 4. Update MongoDB
                try:
                    update_result = platforms.update_one(
                        {"slug": slug},
                        {"$set": {"theCrowdSpace": scraped_data}}
                    )

                    if update_result.modified_count > 0:
                        logger.info(f"Successfully updated 'theCrowdSpace' for company '{slug}'.")
                    elif update_result.matched_count > 0:
                        logger.info(f"Platform '{slug}' matched, but no changes needed (content identical).")
                    else:
                        logger.warning(f"Could not update company '{slug}' (No match found during update phase).")
                        
                except Exception as e:
                    logger.error(f"Database update failed for '{slug}': {e}", exc_info=True)

    except Exception as e:
        logger.critical(f"An unexpected error occurred during execution: {e}", exc_info=True)

    logger.info("Workflow execution finished.")

if __name__ == "__main__":
    process_platforms()
