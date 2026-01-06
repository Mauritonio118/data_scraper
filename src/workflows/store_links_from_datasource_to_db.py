import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Ensure src is in path if running as script
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.DB.platforms_querys import platforms
from src.analizers.store_links_selector import analyze_store_links, verify_links_existence, format_store_links_for_model

# Setup logging
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f'store_links_extraction_{timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def process_store_links():
    logging.info("Starting store links extraction workflow.")
    
    # 1. Extract slugs of platforms that are NO inactive (active or undefined, but specifically not 'inactive')
    # User said: "empresas que NO sean inactivas"
    query = {"operational.status": {"$ne": "inactive"}}
    
    # We need dataSources too to find the links
    projection = {"slug": 1, "dataSources": 1}
    
    try:
        # Get total count for progress tracking
        total_platforms = platforms.count_documents(query)
        cursor = platforms.find(query, projection)
        
        logging.info(f"Found {total_platforms} platforms to process (status != 'inactive').")
        
        processed_count = 0
        updated_count = 0
        
        for doc in cursor:
            slug = doc.get('slug')
            data_sources = doc.get('dataSources', [])
            
            if not slug:
                continue
            
            logging.info(f"Processing platform: {slug}")
            
            # 2. Find all urls with role: "store_listing"
            store_listing_urls = []
            if isinstance(data_sources, list):
                for ds in data_sources:
                    if isinstance(ds, dict) and ds.get('role') == 'store_listing':
                        url = ds.get('url')
                        if url and isinstance(url, str):
                            store_listing_urls.append(url)
            
            logging.info(f"  Found {len(store_listing_urls)} raw store_listing inputs.")

            # 3. Pipeline
            # analyze_store_links -> verify_links_existence -> format_store_links_for_model
            
            # Step A: Analyze and select candidates
            analyzed_urls = analyze_store_links(store_listing_urls)
            
            # Step B: Verify they actually exist (HTTP 200)
            verified_urls = verify_links_existence(analyzed_urls)
            
            # Step C: Format for DB
            output = format_store_links_for_model(verified_urls)
            
            # 4. Save to DB
            # We always save the output, even if empty, to reflect the current reality
            # (e.g. if it had apps before but now links are dead, it should be updated)
            
            try:
                if output:
                    platforms.update_one(
                        {"slug": slug}, 
                        {"$set": {"mobileApps": output}}
                    )
                    logging.info(f"  -> Saved {len(output)} apps: {output}")
                    updated_count += 1
                else:
                    logging.info(f"  -> No valid apps found. Skipping DB update.")
                    
            except Exception as e:
                logging.error(f"  Error updating database for {slug}: {e}")

            processed_count += 1
            if processed_count % 10 == 0:
                logging.info(f"Progress: {processed_count}/{total_platforms}")

        logging.info("Workflow completed successfully.")
        logging.info(f"Total Processed: {processed_count}")
        logging.info(f"Companies with apps found: {updated_count}")
        logging.info(f"Logs saved to: {log_file}")
        
    except Exception as e:
        logging.error(f"Critical error in workflow: {e}", exc_info=True)

if __name__ == "__main__":
    process_store_links()
