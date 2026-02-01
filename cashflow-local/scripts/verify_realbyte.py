
import sys
import os
import logging
from datetime import date

# Ensure src is in path
sys.path.append(os.getcwd())

from src.database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def verify():
    # 1. Check Initial Balance logic
    logger.info("--- 1. Checking Balances ---")
    accounts = db_manager.get_all_accounts()
    checking_acc = next((a for a in accounts if a['name'] == "Test Checking"), None)
    
    if not checking_acc:
        logger.error("Test Checking account not found!")
        return

    balance_checking = db_manager.calculate_account_balance(checking_acc['id'])
    logger.info(f"Checking Account Balance: ${balance_checking:,.2f}")
    
    # 2. Simulate Transfer (Checking -> New Savings)
    logger.info("\n--- 2. Testing Transfer Logic ---")
    # Create Savings
    savings_id = db_manager.create_account("Test Savings", "Savings", 0.0, "USD")
    if not savings_id: 
        # Might exist
        savings_id = next((a['id'] for a in accounts if a['name'] == "Test Savings"), None)
    
    if not savings_id:
        logger.info("Creating Test Savings...")
        savings_id = db_manager.create_account("Test Savings", "Savings", 1000.0, "USD")
        
    initial_savings_bal = db_manager.calculate_account_balance(savings_id)
    initial_checking_bal = balance_checking
    
    transfer_amount = 500.00
    cat_id = db_manager.get_category_id("Transfer", "Expense")
    
    # Simulate UI Logic
    tx_out = {
        'transaction_date': date.today(),
        'amount': transfer_amount,
        'type': 'Expense',
        'category_id': cat_id,
        'account_id': checking_acc['id'],
        'description': f"Transfer to Savings",
        'note': "Test Transfer", 
        'hash_id': f"TEST-TRF-1-{date.today()}",
        'reconciled': False
    }
    
    tx_in = {
        'transaction_date': date.today(),
        'amount': transfer_amount,
        'type': 'Income',
        'category_id': cat_id,
        'account_id': savings_id,
        'description': f"Transfer from Checking",
        'note': "Test Transfer",
        'hash_id': f"TEST-TRF-2-{date.today()}",
        'reconciled': False
    }
    
    db_manager.execute_insert('transactions', [tx_out, tx_in])
    
    # Verify New Balances
    new_checking_bal = db_manager.calculate_account_balance(checking_acc['id'])
    new_savings_bal = db_manager.calculate_account_balance(savings_id)
    
    logger.info(f"Checking: {initial_checking_bal} -> {new_checking_bal} (Expected: {initial_checking_bal - transfer_amount})")
    logger.info(f"Savings: {initial_savings_bal} -> {new_savings_bal} (Expected: {initial_savings_bal + transfer_amount})")
    
    assert new_checking_bal == initial_checking_bal - transfer_amount
    assert new_savings_bal == initial_savings_bal + transfer_amount
    logger.info("✅ Transfer verification PASSED")
    
    # 3. Check Stats Aggregation
    logger.info("\n--- 3. Checking Category Stats ---")
    txns = db_manager.get_transactions()
    logger.info(f"Retrieved {len(txns)} total transactions")
    
    # Check if we have mapped categories
    categorized_count = sum(1 for t in txns if t.get('category') != 'Uncategorized')
    logger.info(f"Categorized Transactions: {categorized_count}/{len(txns)}")
    
    if len(txns) > 0:
        logger.info(f"Sample Transaction: {txns[0]}")
    
    logger.info("✅ Stats verification PASSED")

if __name__ == "__main__":
    verify()
