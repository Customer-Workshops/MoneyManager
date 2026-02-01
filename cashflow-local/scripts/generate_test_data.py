
import sys
import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Ensure src is in path
sys.path.append(os.getcwd())

from src.database import db_manager
from src.deduplication import insert_transactions
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_data(start_year=2024, end_year=2026):
    try:
        # 1. Create Account
        logger.info("Ensuring test account exists...")
        account_id = None
        accounts = db_manager.get_all_accounts()
        
        for acc in accounts:
            if acc['name'] == "Test Checking":
                account_id = acc['id']
                logger.info(f"Found existing 'Test Checking' account (ID: {account_id})")
                break
        
        if not account_id:
            account_id = db_manager.create_account(
                name="Test Checking", 
                type="Checking Account", 
                balance=5000.0, 
                currency="USD"
            )
            logger.info(f"Created 'Test Checking' account (ID: {account_id})")

        # 2. Generate Transactions
        transactions = []
        
        start_date = datetime(start_year, 1, 1)
        end_date = datetime.now()
        
        current_date = start_date
        
        categories = ["Coffee", "Transportation", "Shopping", "Entertainment", "Groceries", "Dining"]
        companies = {
            "Coffee": ["Starbucks", "Dunkin", "Local Cafe"],
            "Transportation": ["Uber", "Lyft", "Shell", "Exxon"],
            "Shopping": ["Amazon", "Target", "Walmart", "Best Buy"],
            "Entertainment": ["Netflix", "Spotify", "AMC Theaters", "Steam"],
            "Groceries": ["Whole Foods", "Trader Joe's", "Kroger", "Safeway"],
            "Dining": ["McDonalds", "Chipotle", "Olive Garden", "Local Pizza"]
        }

        while current_date <= end_date:
            # Monthly Salary (1st or 2nd of month)
            if current_date.day == 1:
                transactions.append({
                    'transaction_date': current_date,
                    'description': 'Payroll: Tech Corp Inc',
                    'amount': 4500.00,
                    'type': 'Credit',
                    'category': 'Salary'
                })
                
                # Monthly Rent (1st of month)
                transactions.append({
                    'transaction_date': current_date,
                    'description': 'Rent Payment',
                    'amount': 1500.00,
                    'type': 'Debit',
                    'category': 'Housing'
                })
                
                # Monthly Utilities (around 1st-5th)
                transactions.append({
                    'transaction_date': current_date + timedelta(days=random.randint(0, 4)),
                    'description': 'Electric Utility Co',
                    'amount': random.uniform(80.0, 150.0),
                    'type': 'Debit',
                    'category': 'Utilities'
                })

            # Random daily expenses
            if random.random() < 0.6: # 60% chance of distinct transaction(s) per day
                num_txns = random.randint(1, 3)
                for _ in range(num_txns):
                    cat = random.choice(categories)
                    desc = random.choice(companies[cat])
                    
                    if cat == "Coffee":
                        amount = random.uniform(4.0, 15.0)
                    elif cat == "Groceries":
                        amount = random.uniform(30.0, 200.0)
                    elif cat == "Dining":
                        amount = random.uniform(15.0, 80.0)
                    elif cat == "Shopping":
                        amount = random.uniform(10.0, 150.0)
                    elif cat == "Transportation": 
                        amount = random.uniform(10.0, 50.0)
                    elif cat == "Entertainment":
                        amount = random.uniform(10.0, 60.0)
                    else:
                        amount = random.uniform(5.0, 50.0)
                        
                    transactions.append({
                        'transaction_date': current_date,
                        'description': f"{desc} {current_date.strftime('%m/%d')}", # Unify description a bit
                        'amount': round(amount, 2),
                        'type': 'Debit',
                        'category': cat
                    })
            
            current_date += timedelta(days=1)

        # 3. Create DataFrame and Insert
        df = pd.DataFrame(transactions)
        logger.info(f"Generated {len(df)} transactions. Inserting...")
        
        # Use a dummy source file hash
        source_hash = f"test_data_{int(datetime.now().timestamp())}"
        
        stats = insert_transactions(df, source_hash, db_manager, account_id=account_id)
        
        logger.info(f"Insertion Stats: {stats}")
        logger.info("Done!")

    except Exception as e:
        logger.error(f"Failed to generate data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_data()
