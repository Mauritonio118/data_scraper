import csv
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Ensure we can import from src
import sys
# Assuming we run from project root, add it to path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.DB.mongo import get_db

# Setup logging
log_dir = os.path.join(current_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"update_status_{timestamp}.log")

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_platforms_collection():
    db = get_db()
    return db["platforms"]

def process_platform_status(row: Dict[str, str], collection):
    company_id = row.get("ID", "Unknown")
    slug = row.get("Slug", "").strip()
    csv_active = row.get("Active", "").strip()

    if not slug:
        logger.warning(f"ID {company_id}: Slug is empty. Skipping.")
        return

    # 1. Validate Slug exists in DB
    company_doc = collection.find_one({"slug": slug})
    if not company_doc:
        logger.warning(f"ID {company_id}: Company with slug '{slug}' not found in database.")
        return

    # 2. Check theCrowdSpace field
    the_crowd_space = company_doc.get("theCrowdSpace")
    crowd_status = None
    
    if the_crowd_space:
        sidebar = the_crowd_space.get("sidebar")
        if sidebar:
            crowd_status = sidebar.get("status")
            if not crowd_status:
                logger.warning(f"ID {company_id}: 'theCrowdSpace' exists but 'status' is missing in sidebar.")
        else:
             logger.warning(f"ID {company_id}: 'theCrowdSpace' exists but 'sidebar' is missing.")
    
    # 3. Determine Logic
    # Values for crowd_status (normalized to lower case if needed, but model says "active", "inactive")
    # Values for csv_active: "SI", "No", "Incierto"
    
    new_status = None
    update_note = None
    
    # Check for Conflicts first
    # Conflict 1: Active=active vs CSV=No
    if crowd_status == "active" and csv_active == "No":
        logger.warning(f"ID {company_id}: CONFLICT - CrowdSpace is 'active' but CSV Active is 'No'. No update performed.")
        return

    # Conflict 2: Inactive=inactive vs CSV=SI
    if crowd_status == "inactive" and csv_active == "SI":
        logger.warning(f"ID {company_id}: CONFLICT - CrowdSpace is 'inactive' but CSV Active is 'SI'. No update performed.")
        return

    # Update Logic
    # Rule 1: active + SI -> active
    if crowd_status == "active" and csv_active == "SI":
        new_status = "active"
        update_note = "Confirmed Active by CrowdSpace and CSV (SI)"
        
    # Rule 2: uncertain + SI -> active
    elif crowd_status == "uncertain" and csv_active == "SI":
        new_status = "active"
        update_note = "Resolved 'uncertain' to 'active' based on CSV (SI)"
        
    # Rule 3: Active is SI (and not conflict/inactive) -> active
    elif csv_active == "SI":
        # This covers cases where crowd_status is None, or 'in_development', or anything not 'inactive'
        new_status = "active"
        update_note = "Set to 'active' based on CSV (SI)"
        
    # Rule 4: inactive + No -> inactive
    elif crowd_status == "inactive" and csv_active == "No":
        new_status = "inactive"
        update_note = "Confirmed Inactive by CrowdSpace and CSV (No)"
        
    # Rule 5: inactive + Incierto -> inactive
    elif crowd_status == "inactive" and csv_active == "Incierto":
        new_status = "inactive"
        update_note = "Retained 'inactive' from CrowdSpace despite CSV 'Incierto'"
        
    # Rule 6: inactive (and match passed) -> inactive
    elif crowd_status == "inactive":
        # csv_active is not SI (conflict checked) and not No/Incierto (checked above)
        new_status = "inactive"
        update_note = "Retained 'inactive' from CrowdSpace"

    # Perform Update if applicable
    if new_status:
        # Check current values to avoid unnecessary writes if exact same state
        current_op = company_doc.get("operational", {})
        if current_op.get("status") == new_status and current_op.get("notes") == update_note:
             logger.info(f"ID {company_id}: Status already '{new_status}' with same note. No change needed.")
        else:
            updated_at = datetime.utcnow().isoformat() + "Z"
            update_result = collection.update_one(
                {"_id": company_doc["_id"]},
                {
                    "$set": {
                        "operational.status": new_status,
                        "operational.notes": update_note,
                        "operational.updatedAt": updated_at
                    }
                }
            )
            if update_result.modified_count > 0:
                logger.info(f"ID {company_id}: UPDATED status to '{new_status}'. Note: {update_note}")
            else:
                logger.info(f"ID {company_id}: No changes made (DB match during update op).")
    else:
        logger.info(f"ID {company_id}: No matching rule for CS='{crowd_status}' / CSV='{csv_active}'. No update.")

def main():
    csv_path = os.path.join(current_dir, "src", "workflows", "companies_list.csv")
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        return

    collection = get_platforms_collection()
    logger.info(f"Starting workflow processing from {csv_path}")
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            count = 0
            for row in reader:
                process_platform_status(row, collection)
                count += 1
                
            logger.info(f"Finished processing {count} rows.")
            
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}", exc_info=True)

if __name__ == "__main__":
    main()
