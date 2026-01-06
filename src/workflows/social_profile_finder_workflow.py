import logging
import os
import sys
from datetime import datetime
from src.DB.platforms_querys import get_slugs_not_inactive, delete_social_profiles_field
from src.analizers.social_profile_selector import analyze_and_store_social_profiles

# Configuration
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "social_profile_finder_workflow.log")
RESET_ALL_PROFILES = True # Set to True to clear all social profiles before processing

def setup_logging():
    """Configures logging to file and console."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    # Configure root logger to capture logs from imported modules
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s') # Keep console clean
    console_handler.setFormatter(console_formatter)
    
    # Clear existing handlers to avoid duplicates if run multiple times
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def run_workflow():
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info(f"STARTING SOCIAL PROFILE DISCOVERY WORKFLOW - {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        # 1. Get Slugs
        logger.info("Fetching active company slugs...")
        slugs = get_slugs_not_inactive()
        logger.info(f"Found {len(slugs)} platforms to process.")
        
        # 1.5. Reset Mode
        if RESET_ALL_PROFILES:
            logger.info("!" * 60)
            logger.info("RESET MODE ENABLED: DELETING 'socialProfiles' FIELD FROM ALL PLATFORMS")
            logger.info("!" * 60)
            for slug in slugs:
                res = delete_social_profiles_field(slug)
                logger.info(f"  [RESET] {slug}: {res}")
            logger.info("-" * 40)

        # 2. Iterate and Process
        total_processed = 0
        total_stored = 0
        
        for i, slug in enumerate(slugs, 1):
            logger.info("-" * 40)
            logger.info(f"Processing ({i}/{len(slugs)}): {slug}")
            
            try:
                stats = analyze_and_store_social_profiles(slug)
                
                # Format friendly log based on stats, handling implicit failures gracefully
                cand_found = stats.get("candidates_found", 0)
                if cand_found == 0:
                    logger.info(f"  -> No candidates found.")
                else:
                    logger.info(f"  -> Candidates: {cand_found}")
                    logger.info(f"  -> Valid Profiles: {stats.get('valid_profiles', 0)}")
                    logger.info(f"  -> DB Stored/Updated: {stats.get('stored', 0)}")
                
                total_stored += stats.get("stored", 0)
                
            except Exception as e:
                logger.error(f"Error processing {slug}: {str(e)}", exc_info=True)
            
            total_processed += 1
            
        logger.info("=" * 60)
        logger.info(f"WORKFLOW COMPLETED")
        logger.info(f"Total Platforms Processed: {total_processed}")
        logger.info(f"Total Profiles Stored/Updated: {total_stored}")
        logger.info(f"Logs saved to: {os.path.abspath(LOG_FILE)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.critical(f"Critical Workflow Error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    run_workflow()
