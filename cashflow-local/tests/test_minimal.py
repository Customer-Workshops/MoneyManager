
import sys
import os
# Ensure src is in path
sys.path.append(os.getcwd())

from src.database import db_manager
import logging

logging.basicConfig(level=logging.INFO)

try:
    print("Testing create_account...")
    aid = db_manager.create_account("MinTest", "Checking", 100.0, "USD")
    print(f"Created account ID: {aid}")
    
    print("Testing get_account_by_id...")
    acc = db_manager.get_account_by_id(aid)
    print(f"Retrieved account: {acc}")
    
    if acc and acc['name'] == "MinTest" and acc['type'] == "Checking":
        print("SUCCESS")
    else:
        print("FAILURE: Account data mismatch")
        
except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
