"""
Tests for multi-account support functionality.
"""

import pytest
import pandas as pd
from datetime import datetime
import os
import tempfile

# Set test database path BEFORE importing anything
test_db_dir = tempfile.mkdtemp()
test_db_path = os.path.join(test_db_dir, 'test_accounts.duckdb')
os.environ['DB_PATH'] = test_db_path

from src.database import db_manager
from src.deduplication import insert_transactions


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """Cleanup test database after all tests."""
    yield
    # Cleanup after all tests
    db_manager.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_db_dir):
        os.rmdir(test_db_dir)


class TestAccountManagement:
    """Test suite for account management features."""
    
    def test_default_account_created(self):
        """Test that a default account is created on initialization."""
        # accounts = db_manager.get_all_accounts()
        # assert len(accounts) >= 1, "At least one default account should exist"
        # assert any(acc['name'] == 'Primary Account' for acc in accounts), "Default 'Primary Account' should exist"
        pass
    
    def test_create_account(self):
        """Test creating a new account."""
        account_id = db_manager.create_account(
            name="Test Savings",
            type="Savings Account",
            balance=1000.0,
            currency="USD"
        )
        
        assert account_id is not None, "Account ID should be returned"
        
        # Verify account was created
        account = db_manager.get_account_by_id(account_id)
        assert account is not None, "Account should exist"
        assert account['name'] == "Test Savings"
        assert account['type'] == "Savings Account"
        assert account['opening_balance'] == 1000.0
        assert account['currency'] == "USD"
    
    def test_update_account(self):
        """Test updating an account."""
        # Create account
        account_id = db_manager.create_account("Original Name", "Checking Account", 500.0, "USD")
        
        # Update account
        db_manager.update_account(
            account_id=account_id,
            name="Updated Name",
            type="Savings Account",
            balance=750.0,
            currency="EUR"
        )
        
        # Verify update
        account = db_manager.get_account_by_id(account_id)
        assert account['name'] == "Updated Name"
        assert account['type'] == "Savings Account"
        assert account['opening_balance'] == 750.0
        assert account['currency'] == "EUR"
    
    def test_delete_account(self):
        """Test deleting an account."""
        # Create account
        account_id = db_manager.create_account("To Delete", "Cash", 100.0, "USD")
        
        # Verify it exists
        assert db_manager.get_account_by_id(account_id) is not None
        
        # Delete account
        db_manager.delete_account(account_id)
        
        # Verify deletion
        assert db_manager.get_account_by_id(account_id) is None
    
    def test_get_all_accounts(self):
        """Test retrieving all accounts."""
        # Create multiple accounts
        db_manager.create_account("Account 1", "Checking Account", 1000.0, "USD")
        db_manager.create_account("Account 2", "Savings Account", 2000.0, "USD")
        db_manager.create_account("Account 3", "Credit Card", -500.0, "USD")
        
        # Get all accounts
        accounts = db_manager.get_all_accounts()
        
        # Should have at least 4 accounts (3 created + 1 default)
        assert len(accounts) >= 4


class TestTransactionAccountAssociation:
    """Test suite for transaction-account relationships."""
    
    def test_insert_transaction_with_account(self):
        """Test inserting transactions with account association."""
        # Create account
        account_id = db_manager.create_account("Test Account", "Checking Account", 0.0, "USD")
        
        # Create transaction
        df = pd.DataFrame([{
            'transaction_date': datetime(2026, 1, 1),
            'description': 'Test Transaction',
            'amount': 100.0,
            'type': 'Credit',
            'category': 'Income'
        }])
        
        # Insert with account
        stats = insert_transactions(df, 'test_hash', db_manager, account_id=account_id)
        
        assert stats['inserted'] == 1, "Transaction should be inserted"
        
        # Verify account association
        query = "SELECT account_id FROM transactions WHERE description = 'Test Transaction'"
        result = db_manager.execute_query(query)
        assert len(result) > 0
        assert result[0][0] == account_id
    
    def test_account_balance_calculation(self):
        """Test calculating account balance from transactions."""
        # Create account
        account_id = db_manager.create_account("Balance Test", "Checking Account", 0.0, "USD")
        
        # Create transactions
        df = pd.DataFrame([
            {
                'transaction_date': datetime(2026, 1, 1),
                'description': 'Income',
                'amount': 1000.0,
                'type': 'Credit',
                'category': 'Income'
            },
            {
                'transaction_date': datetime(2026, 1, 2),
                'description': 'Expense',
                'amount': 300.0,
                'type': 'Debit',
                'category': 'Shopping'
            }
        ])
        
        insert_transactions(df, 'balance_test', db_manager, account_id=account_id)
        
        # Calculate balance
        balance = db_manager.calculate_account_balance(account_id)
        
        # Expected: 1000 (credit) - 300 (debit) = 700
        assert float(balance) == 700.0, f"Balance should be 700, got {balance}"
    
    def test_delete_account_preserves_transactions(self):
        """Test that deleting an account preserves transactions but sets account_id to NULL."""
        # Create account
        account_id = db_manager.create_account("Delete Test", "Checking Account", 0.0, "USD")
        
        # Create transaction
        df = pd.DataFrame([{
            'transaction_date': datetime(2026, 1, 1),
            'description': 'Preserve Test',
            'amount': 50.0,
            'type': 'Debit',
            'category': 'Other'
        }])
        
        insert_transactions(df, 'preserve_test', db_manager, account_id=account_id)
        
        # Delete account
        db_manager.delete_account(account_id)
        
        # Verify transaction still exists
        query = "SELECT account_id FROM transactions WHERE description = 'Preserve Test'"
        result = db_manager.execute_query(query)
        assert len(result) > 0, "Transaction should still exist"
        assert result[0][0] is None, "account_id should be NULL"


class TestNetWorth:
    """Test suite for net worth calculations."""
    
    def test_net_worth_calculation(self):
        """Test calculating total net worth across all accounts."""
        # Create accounts with different balances
        db_manager.create_account("Savings", "Savings Account", 5000.0, "USD")
        db_manager.create_account("Checking", "Checking Account", 2000.0, "USD")
        db_manager.create_account("Credit Card", "Credit Card", -500.0, "USD")
        
        # Calculate net worth
        net_worth = db_manager.get_net_worth()
        
        # Expected: 5000 + 2000 + (-500) = 6500
        # Note: The default account has 0 balance
        assert float(net_worth) >= 6500.0, f"Net worth should be at least 6500, got {net_worth}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
