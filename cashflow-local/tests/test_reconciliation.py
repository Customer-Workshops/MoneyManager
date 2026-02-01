"""
Tests for Bank Account Reconciliation & Balance Tracking Feature

Tests the reconciliation engine, balance calculations, and variance detection.
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from src.database import DatabaseManager
from src.reconciliation import ReconciliationEngine


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.duckdb')
    os.close(temp_fd)
    
    # Set database path
    os.environ['DB_PATH'] = temp_path
    
    # Create a new database manager instance
    db_manager = DatabaseManager()
    
    yield db_manager
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_account(temp_db):
    """Create a sample account for testing."""
    account_data = {
        'name': 'Test Account',
        'account_number': '1234',
        'account_type': 'Savings',
        'opening_balance': 1000.00,
        'opening_balance_date': datetime(2025, 1, 1).date(),
        'currency': 'INR',
        'is_active': True
    }
    
    temp_db.execute_insert('accounts', [account_data])
    
    # Get the created account
    accounts = temp_db.get_accounts()
    return accounts[0]


@pytest.fixture
def sample_transactions(temp_db, sample_account):
    """Create sample transactions for testing."""
    transactions = [
        {
            'hash': 'hash1',
            'transaction_date': datetime(2025, 1, 5).date(),
            'description': 'Salary Deposit',
            'amount': 5000.00,
            'type': 'Credit',
            'category': 'Income',
            'source_file_hash': 'file1',
            'account_id': sample_account['id'],
            'reconciled': False
        },
        {
            'hash': 'hash2',
            'transaction_date': datetime(2025, 1, 10).date(),
            'description': 'Grocery Store',
            'amount': 500.00,
            'type': 'Debit',
            'category': 'Groceries',
            'source_file_hash': 'file1',
            'account_id': sample_account['id'],
            'reconciled': False
        },
        {
            'hash': 'hash3',
            'transaction_date': datetime(2025, 1, 15).date(),
            'description': 'Rent Payment',
            'amount': 2000.00,
            'type': 'Debit',
            'category': 'Housing',
            'source_file_hash': 'file1',
            'account_id': sample_account['id'],
            'reconciled': False
        },
    ]
    
    temp_db.execute_insert('transactions', transactions)
    return transactions


def test_account_creation(temp_db):
    """Test creating a new account."""
    account_data = {
        'name': 'Test Checking Account',
        'account_number': '5678',
        'account_type': 'Checking',
        'opening_balance': 500.00,
        'opening_balance_date': datetime(2025, 1, 1).date(),
        'currency': 'USD',
        'is_active': True
    }
    
    temp_db.execute_insert('accounts', [account_data])
    
    # Verify account was created
    accounts = temp_db.get_accounts()
    assert len(accounts) == 1
    assert accounts[0]['name'] == 'Test Checking Account'
    assert accounts[0]['opening_balance'] == 500.00


def test_calculate_account_balance(temp_db, sample_account, sample_transactions):
    """Test balance calculation with opening balance and transactions."""
    # Expected: 1000 (opening) + 5000 (credit) - 500 (debit) - 2000 (debit) = 3500
    balance = temp_db.calculate_account_balance(
        account_id=sample_account['id'],
        as_of_date=datetime(2025, 1, 31).date()
    )
    
    assert balance == 3500.00


def test_calculate_balance_as_of_date(temp_db, sample_account, sample_transactions):
    """Test balance calculation as of a specific date."""
    # As of Jan 12, only salary and grocery should be included
    # Expected: 1000 + 5000 - 500 = 5500
    balance = temp_db.calculate_account_balance(
        account_id=sample_account['id'],
        as_of_date=datetime(2025, 1, 12).date()
    )
    
    assert balance == 5500.00


def test_mark_transactions_reconciled(temp_db, sample_account, sample_transactions):
    """Test marking transactions as reconciled."""
    # Get all transactions
    txns = temp_db.get_transactions(account_id=sample_account['id'])
    txn_ids = [t['id'] for t in txns]
    
    # Mark first two as reconciled
    count = temp_db.mark_transactions_reconciled(txn_ids[:2], reconciled=True)
    
    assert count == 2
    
    # Verify reconciled status
    reconciled_txns = temp_db.get_transactions(
        account_id=sample_account['id'],
        reconciled=True
    )
    
    assert len(reconciled_txns) == 2


def test_save_balance_snapshot(temp_db, sample_account):
    """Test saving a balance snapshot."""
    snapshot_date = datetime(2025, 1, 31).date()
    
    temp_db.save_balance_snapshot(
        account_id=sample_account['id'],
        balance_date=snapshot_date,
        calculated_balance=3500.00,
        actual_balance=3450.00,
        notes="Monthly reconciliation"
    )
    
    # Verify snapshot was saved
    history = temp_db.get_balance_history(
        account_id=sample_account['id']
    )
    
    assert len(history) == 1
    assert history[0]['calculated_balance'] == 3500.00
    assert history[0]['actual_balance'] == 3450.00
    assert history[0]['variance'] == -50.00
    assert not history[0]['is_reconciled']  # Variance > 0.01


def test_variance_detection(temp_db, sample_account, sample_transactions):
    """Test variance detection between calculated and actual balance."""
    reconciliation_engine = ReconciliationEngine(temp_db)
    
    statement_date = datetime(2025, 1, 31).date()
    statement_balance = 3450.00  # Actual bank balance
    
    analysis = reconciliation_engine.analyze_variance(
        account_id=sample_account['id'],
        statement_date=statement_date,
        statement_balance=statement_balance
    )
    
    assert analysis['calculated_balance'] == 3500.00
    assert analysis['statement_balance'] == 3450.00
    assert analysis['variance'] == -50.00
    assert not analysis['is_reconciled']  # Variance too large
    assert analysis['unreconciled_count'] == 3


def test_duplicate_detection(temp_db, sample_account):
    """Test duplicate transaction detection."""
    # Create potential duplicates
    transactions = [
        {
            'hash': 'hash_d1',
            'transaction_date': datetime(2025, 2, 1).date(),
            'description': 'COFFEE SHOP',
            'amount': 5.50,
            'type': 'Debit',
            'category': 'Food',
            'source_file_hash': 'file2',
            'account_id': sample_account['id'],
            'reconciled': False
        },
        {
            'hash': 'hash_d2',
            'transaction_date': datetime(2025, 2, 2).date(),  # 1 day apart
            'description': 'COFFEE SHOP',
            'amount': 5.50,
            'type': 'Debit',
            'category': 'Food',
            'source_file_hash': 'file2',
            'account_id': sample_account['id'],
            'reconciled': False
        },
    ]
    
    temp_db.execute_insert('transactions', transactions)
    
    reconciliation_engine = ReconciliationEngine(temp_db)
    duplicates = reconciliation_engine.detect_duplicates(
        account_id=sample_account['id'],
        threshold_days=3,
        amount_tolerance=0.01
    )
    
    assert len(duplicates) > 0
    assert duplicates[0]['transaction1']['description'] == 'COFFEE SHOP'
    assert duplicates[0]['transaction2']['description'] == 'COFFEE SHOP'


def test_suggest_missing_transactions(temp_db, sample_account, sample_transactions):
    """Test missing transaction suggestions."""
    reconciliation_engine = ReconciliationEngine(temp_db)
    
    # Expected balance is higher than calculated (missing income)
    suggestions = reconciliation_engine.suggest_missing_transactions(
        account_id=sample_account['id'],
        start_date=datetime(2025, 1, 1).date(),
        end_date=datetime(2025, 1, 31).date(),
        expected_balance=4000.00  # 500 more than calculated 3500
    )
    
    assert len(suggestions) > 0
    assert any('income' in s.lower() or 'credit' in s.lower() for s in suggestions)


def test_generate_reconciliation_report(temp_db, sample_account, sample_transactions):
    """Test comprehensive reconciliation report generation."""
    reconciliation_engine = ReconciliationEngine(temp_db)
    
    report = reconciliation_engine.generate_reconciliation_report(
        account_id=sample_account['id'],
        start_date=datetime(2025, 1, 1).date(),
        end_date=datetime(2025, 1, 31).date()
    )
    
    assert report['account']['id'] == sample_account['id']
    assert report['summary']['total_transactions'] == 3
    assert report['summary']['reconciled_count'] == 0
    assert report['summary']['unreconciled_count'] == 3
    assert report['summary']['opening_balance'] == 1000.00
    assert report['summary']['closing_balance'] == 3500.00


def test_get_transactions_with_filters(temp_db, sample_account, sample_transactions):
    """Test retrieving transactions with various filters."""
    # Test account filter
    txns = temp_db.get_transactions(account_id=sample_account['id'])
    assert len(txns) == 3
    
    # Test date filter
    txns = temp_db.get_transactions(
        account_id=sample_account['id'],
        start_date=datetime(2025, 1, 10).date()
    )
    assert len(txns) == 2  # Only grocery and rent
    
    # Test reconciled filter
    txns = temp_db.get_transactions(
        account_id=sample_account['id'],
        reconciled=False
    )
    assert len(txns) == 3  # All unreconciled


def test_balance_history_retrieval(temp_db, sample_account):
    """Test retrieving balance history with filters."""
    # Create multiple snapshots
    snapshots = [
        (datetime(2025, 1, 31).date(), 3500.00, 3500.00),
        (datetime(2025, 2, 28).date(), 4000.00, 3950.00),
        (datetime(2025, 3, 31).date(), 4500.00, 4500.00),
    ]
    
    for date, calc_bal, actual_bal in snapshots:
        temp_db.save_balance_snapshot(
            account_id=sample_account['id'],
            balance_date=date,
            calculated_balance=calc_bal,
            actual_balance=actual_bal
        )
    
    # Get all history
    history = temp_db.get_balance_history(account_id=sample_account['id'])
    assert len(history) == 3
    
    # Get filtered history
    history = temp_db.get_balance_history(
        account_id=sample_account['id'],
        start_date=datetime(2025, 2, 1).date(),
        end_date=datetime(2025, 2, 28).date()
    )
    assert len(history) == 1
    assert history[0]['balance_date'] == datetime(2025, 2, 28).date()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
