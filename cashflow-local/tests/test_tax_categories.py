"""
Tests for Tax Category Management functionality
"""

import pytest
from datetime import datetime, date
from src.database import DatabaseManager


class TestTaxCategories:
    """Test tax category operations."""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary database for testing."""
        import os
        db_path = tmp_path / "test_tax.duckdb"
        os.environ["DB_PATH"] = str(db_path)
        
        # Create new instance
        db_manager = DatabaseManager()
        yield db_manager
        
        # Cleanup
        db_manager.close()
    
    def test_tax_categories_initialized(self, db):
        """Test that predefined tax categories are created."""
        categories = db.get_all_tax_categories()
        
        assert len(categories) > 0, "Tax categories should be initialized"
        
        # Check for specific categories
        category_names = [cat['name'] for cat in categories]
        assert '80C - Investments' in category_names
        assert '80D - Health Insurance' in category_names
        assert 'HRA - House Rent' in category_names
    
    def test_tax_category_limits(self, db):
        """Test that tax categories have correct limits."""
        categories = db.get_all_tax_categories()
        
        # Find 80C category
        cat_80c = next((cat for cat in categories if cat['section'] == '80C'), None)
        assert cat_80c is not None
        assert cat_80c['annual_limit'] == 150000.00
        
        # Find 80D category
        cat_80d = next((cat for cat in categories if '80D - Health Insurance' in cat['name']), None)
        assert cat_80d is not None
        assert cat_80d['annual_limit'] == 25000.00
    
    def test_add_tax_tag(self, db):
        """Test adding tax tag to a transaction."""
        # First, insert a test transaction
        test_txn = [{
            'hash': 'test_hash_001',
            'transaction_date': date(2024, 4, 15),
            'description': 'LIC Premium',
            'amount': 25000.00,
            'type': 'Debit',
            'category': 'Insurance',
            'source_file_hash': 'test_source'
        }]
        
        db.execute_insert('transactions', test_txn)
        
        # Get the transaction ID
        with db.get_connection() as conn:
            txn_id = conn.execute("SELECT id FROM transactions WHERE hash = 'test_hash_001'").fetchone()[0]
        
        # Get 80C category ID
        categories = db.get_all_tax_categories()
        cat_80c = next((cat for cat in categories if cat['section'] == '80C'), None)
        
        # Add tax tag
        result = db.add_tax_tag(txn_id, cat_80c['id'])
        assert result is True, "First tag addition should succeed"
        
        # Try adding the same tag again
        result = db.add_tax_tag(txn_id, cat_80c['id'])
        assert result is False, "Duplicate tag addition should fail"
    
    def test_remove_tax_tag(self, db):
        """Test removing tax tag from a transaction."""
        # Setup: Insert transaction and add tag
        test_txn = [{
            'hash': 'test_hash_002',
            'transaction_date': date(2024, 5, 10),
            'description': 'Health Insurance',
            'amount': 15000.00,
            'type': 'Debit',
            'category': 'Insurance',
            'source_file_hash': 'test_source'
        }]
        
        db.execute_insert('transactions', test_txn)
        
        with db.get_connection() as conn:
            txn_id = conn.execute("SELECT id FROM transactions WHERE hash = 'test_hash_002'").fetchone()[0]
        
        categories = db.get_all_tax_categories()
        cat_80d = next((cat for cat in categories if '80D - Health Insurance' in cat['name']), None)
        
        db.add_tax_tag(txn_id, cat_80d['id'])
        
        # Remove the tag
        result = db.remove_tax_tag(txn_id, cat_80d['id'])
        assert result is True
        
        # Verify tag is removed
        tags = db.get_transaction_tax_tags(txn_id)
        assert len(tags) == 0
    
    def test_get_transaction_tax_tags(self, db):
        """Test retrieving tax tags for a transaction."""
        # Setup: Insert transaction with multiple tags
        test_txn = [{
            'hash': 'test_hash_003',
            'transaction_date': date(2024, 6, 20),
            'description': 'Medical Expense',
            'amount': 5000.00,
            'type': 'Debit',
            'category': 'Healthcare',
            'source_file_hash': 'test_source'
        }]
        
        db.execute_insert('transactions', test_txn)
        
        with db.get_connection() as conn:
            txn_id = conn.execute("SELECT id FROM transactions WHERE hash = 'test_hash_003'").fetchone()[0]
        
        categories = db.get_all_tax_categories()
        cat_80d = next((cat for cat in categories if '80D - Health Insurance' in cat['name']), None)
        
        # Add tags
        db.add_tax_tag(txn_id, cat_80d['id'])
        
        # Retrieve tags
        tags = db.get_transaction_tax_tags(txn_id)
        assert len(tags) == 1
        assert tags[0]['section'] == '80D'
    
    def test_tax_summary(self, db):
        """Test tax summary generation."""
        # Setup: Insert transactions with tax tags
        test_txns = [
            {
                'hash': 'test_hash_004',
                'transaction_date': date(2024, 4, 15),
                'description': 'PPF Deposit',
                'amount': 50000.00,
                'type': 'Debit',
                'category': 'Investment',
                'source_file_hash': 'test_source'
            },
            {
                'hash': 'test_hash_005',
                'transaction_date': date(2024, 5, 20),
                'description': 'ELSS Investment',
                'amount': 30000.00,
                'type': 'Debit',
                'category': 'Investment',
                'source_file_hash': 'test_source'
            }
        ]
        
        db.execute_insert('transactions', test_txns)
        
        categories = db.get_all_tax_categories()
        cat_80c = next((cat for cat in categories if cat['section'] == '80C'), None)
        
        # Add tags to both transactions
        with db.get_connection() as conn:
            txn_ids = conn.execute(
                "SELECT id FROM transactions WHERE hash IN ('test_hash_004', 'test_hash_005')"
            ).fetchall()
        
        for txn_id_tuple in txn_ids:
            db.add_tax_tag(txn_id_tuple[0], cat_80c['id'])
        
        # Get tax summary
        summary = db.get_tax_summary(
            start_date=datetime(2024, 4, 1),
            end_date=datetime(2024, 12, 31)
        )
        
        # Find 80C in summary
        cat_80c_summary = next((s for s in summary if s['section'] == '80C'), None)
        assert cat_80c_summary is not None
        assert cat_80c_summary['transaction_count'] == 2
        assert cat_80c_summary['total_amount'] == 80000.00
        
        # Check utilization percentage
        expected_utilization = (80000.00 / 150000.00) * 100
        assert abs(cat_80c_summary['utilization_percent'] - expected_utilization) < 0.01
    
    def test_get_transactions_by_tax_category(self, db):
        """Test retrieving transactions by tax category."""
        # Setup
        test_txns = [
            {
                'hash': 'test_hash_006',
                'transaction_date': date(2024, 7, 10),
                'description': 'Donation to Charity',
                'amount': 10000.00,
                'type': 'Debit',
                'category': 'Donation',
                'source_file_hash': 'test_source'
            }
        ]
        
        db.execute_insert('transactions', test_txns)
        
        with db.get_connection() as conn:
            txn_id = conn.execute("SELECT id FROM transactions WHERE hash = 'test_hash_006'").fetchone()[0]
        
        categories = db.get_all_tax_categories()
        cat_80g = next((cat for cat in categories if cat['section'] == '80G'), None)
        
        db.add_tax_tag(txn_id, cat_80g['id'])
        
        # Get transactions by category
        transactions = db.get_transactions_by_tax_category(
            tax_category_id=cat_80g['id'],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        
        assert len(transactions) == 1
        assert transactions[0]['description'] == 'Donation to Charity'
        assert transactions[0]['amount'] == 10000.00
    
    def test_multiple_tags_per_transaction(self, db):
        """Test that transactions can have multiple tax tags."""
        # A transaction could be both a business expense and eligible for other deductions
        test_txn = [{
            'hash': 'test_hash_007',
            'transaction_date': date(2024, 8, 15),
            'description': 'Office Rent',
            'amount': 20000.00,
            'type': 'Debit',
            'category': 'Business',
            'source_file_hash': 'test_source'
        }]
        
        db.execute_insert('transactions', test_txn)
        
        with db.get_connection() as conn:
            txn_id = conn.execute("SELECT id FROM transactions WHERE hash = 'test_hash_007'").fetchone()[0]
        
        categories = db.get_all_tax_categories()
        cat_business = next((cat for cat in categories if cat['section'] == 'Business'), None)
        cat_hra = next((cat for cat in categories if cat['section'] == 'HRA'), None)
        
        # Add both tags
        db.add_tax_tag(txn_id, cat_business['id'])
        db.add_tax_tag(txn_id, cat_hra['id'])
        
        # Verify both tags are present
        tags = db.get_transaction_tax_tags(txn_id)
        assert len(tags) == 2
        
        sections = {tag['section'] for tag in tags}
        assert 'Business' in sections
        assert 'HRA' in sections
