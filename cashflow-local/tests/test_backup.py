"""
Unit tests for backup and restore functionality.

Tests cover:
- Backup creation
- Backup validation
- Full restore
- Merge restore
- Selective restore
- Backup preview
"""

import pytest
import json
import zipfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.backup import BackupManager, backup_manager
from src.database import db_manager


class TestBackupManager:
    """Test suite for BackupManager class."""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test data before each test."""
        # Clear existing data
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM category_rules")
            conn.execute("DELETE FROM budgets")
        
        # Insert test transactions
        test_transactions = [
            {
                'hash': 'test_hash_1',
                'transaction_date': '2024-01-15',
                'description': 'Grocery Store',
                'amount': 50.00,
                'type': 'Debit',
                'category': 'Groceries',
                'source_file_hash': 'test_file_1'
            },
            {
                'hash': 'test_hash_2',
                'transaction_date': '2024-01-20',
                'description': 'Salary',
                'amount': 3000.00,
                'type': 'Credit',
                'category': 'Income',
                'source_file_hash': 'test_file_1'
            },
            {
                'hash': 'test_hash_3',
                'transaction_date': '2024-02-10',
                'description': 'Restaurant',
                'amount': 75.00,
                'type': 'Debit',
                'category': 'Dining',
                'source_file_hash': 'test_file_1'
            }
        ]
        
        db_manager.execute_insert('transactions', test_transactions)
        
        # Insert test category rules
        test_rules = [
            {'keyword': 'grocery', 'category': 'Groceries'},
            {'keyword': 'restaurant', 'category': 'Dining'}
        ]
        db_manager.execute_insert('category_rules', test_rules)
        
        # Insert test budgets
        test_budgets = [
            {'category': 'Groceries', 'monthly_limit': 500.00},
            {'category': 'Dining', 'monthly_limit': 200.00}
        ]
        db_manager.execute_insert('budgets', test_budgets)
        
        yield
        
        # Cleanup after test
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM category_rules")
            conn.execute("DELETE FROM budgets")
    
    def test_create_backup(self):
        """Test that backup creation produces valid ZIP with correct data."""
        manager = BackupManager()
        
        # Create backup
        zip_bytes, metadata = manager.create_backup()
        
        # Verify we got bytes
        assert zip_bytes is not None
        assert len(zip_bytes) > 0
        
        # Verify metadata
        assert 'backup_date' in metadata
        assert 'statistics' in metadata
        assert metadata['statistics']['total_transactions'] == 3
        assert metadata['statistics']['total_category_rules'] == 2
        assert metadata['statistics']['total_budgets'] == 2
        
        # Verify ZIP is valid
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        try:
            temp_file.write(zip_bytes)
            temp_file.close()
            
            with zipfile.ZipFile(temp_file.name, 'r') as zf:
                files = zf.namelist()
                assert len(files) == 2  # backup JSON + metadata
                assert any('cashflow_backup' in f for f in files)
                assert 'metadata.json' in files
        finally:
            Path(temp_file.name).unlink()
    
    def test_validate_backup_success(self):
        """Test that valid backup passes validation."""
        manager = BackupManager()
        
        # Create backup
        zip_bytes, _ = manager.create_backup()
        
        # Validate
        is_valid, message, backup_data = manager.validate_backup(zip_bytes)
        
        assert is_valid is True
        assert "successful" in message.lower()
        assert backup_data is not None
        assert 'tables' in backup_data
        assert 'transactions' in backup_data['tables']
    
    def test_validate_backup_invalid_zip(self):
        """Test that invalid ZIP fails validation."""
        manager = BackupManager()
        
        # Invalid ZIP bytes
        invalid_bytes = b"This is not a valid ZIP file"
        
        # Validate
        is_valid, message, backup_data = manager.validate_backup(invalid_bytes)
        
        assert is_valid is False
        assert "zip" in message.lower()
        assert backup_data is None
    
    def test_validate_backup_missing_tables(self):
        """Test that backup with missing tables fails validation."""
        manager = BackupManager()
        
        # Create invalid backup (missing required table)
        invalid_backup = {
            "format_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "tables": {
                "transactions": [],
                # Missing category_rules and budgets
            }
        }
        
        # Create ZIP
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        try:
            with zipfile.ZipFile(temp_file.name, 'w') as zf:
                zf.writestr("backup.json", json.dumps(invalid_backup))
            
            with open(temp_file.name, 'rb') as f:
                zip_bytes = f.read()
            
            # Validate
            is_valid, message, backup_data = manager.validate_backup(zip_bytes)
            
            assert is_valid is False
            assert "missing table" in message.lower()
        finally:
            Path(temp_file.name).unlink()
    
    def test_full_restore(self):
        """Test full database restore replaces all data."""
        manager = BackupManager()
        
        # Create backup of current data
        zip_bytes, _ = manager.create_backup()
        
        # Modify database
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM transactions")
            conn.execute(
                "INSERT INTO transactions (hash, transaction_date, description, amount, type, category, source_file_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ['new_hash', '2024-03-01', 'New Transaction', 100.00, 'Debit', 'Other', 'new_file']
            )
        
        # Verify we have 1 transaction
        result = db_manager.execute_query("SELECT COUNT(*) FROM transactions")
        assert result[0][0] == 1
        
        # Restore from backup (full mode)
        success, message, stats = manager.restore_backup(zip_bytes, mode="full")
        
        assert success is True
        assert stats['transactions_restored'] == 3
        
        # Verify we have 3 transactions (original backup data)
        result = db_manager.execute_query("SELECT COUNT(*) FROM transactions")
        assert result[0][0] == 3
    
    def test_merge_restore(self):
        """Test merge restore adds new data without removing existing."""
        manager = BackupManager()
        
        # Create backup of current data (3 transactions)
        zip_bytes, _ = manager.create_backup()
        
        # Add a new transaction to database
        with db_manager.get_connection() as conn:
            conn.execute(
                "INSERT INTO transactions (hash, transaction_date, description, amount, type, category, source_file_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ['new_unique_hash', '2024-03-01', 'New Transaction', 100.00, 'Debit', 'Other', 'new_file']
            )
        
        # Verify we have 4 transactions
        result = db_manager.execute_query("SELECT COUNT(*) FROM transactions")
        assert result[0][0] == 4
        
        # Restore from backup (merge mode)
        success, message, stats = manager.restore_backup(zip_bytes, mode="merge")
        
        assert success is True
        # Should skip 3 duplicates, restore 0 new ones
        assert stats['duplicates_skipped'] == 3
        
        # Verify we still have 4 transactions (1 new + 3 original)
        result = db_manager.execute_query("SELECT COUNT(*) FROM transactions")
        assert result[0][0] == 4
    
    def test_selective_restore(self):
        """Test selective restore only restores transactions in date range."""
        manager = BackupManager()
        
        # Create backup of current data (3 transactions)
        zip_bytes, _ = manager.create_backup()
        
        # Clear all data from database (not just transactions)
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM category_rules")
            conn.execute("DELETE FROM budgets")
        
        # Restore only January transactions
        success, message, stats = manager.restore_backup(
            zip_bytes,
            mode="selective",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert success is True
        assert stats['transactions_restored'] == 2  # Only 2 transactions in January
        
        # Verify we have 2 transactions
        result = db_manager.execute_query("SELECT COUNT(*) FROM transactions")
        assert result[0][0] == 2
    
    def test_get_backup_preview(self):
        """Test backup preview returns correct information."""
        manager = BackupManager()
        
        # Create backup
        zip_bytes, _ = manager.create_backup()
        
        # Get preview
        preview = manager.get_backup_preview(zip_bytes)
        
        assert preview is not None
        assert 'statistics' in preview
        assert preview['statistics']['total_transactions'] == 3
        assert preview['statistics']['total_category_rules'] == 2
        assert preview['statistics']['total_budgets'] == 2
        
        # Check date range
        assert 'date_range' in preview
        assert preview['date_range']['earliest'] == '2024-01-15'
        assert preview['date_range']['latest'] == '2024-02-10'
        
        # Check categories
        assert 'categories' in preview
        assert 'Groceries' in preview['categories']
        assert 'Dining' in preview['categories']
    
    def test_backup_checksum_validation(self):
        """Test that checksum validation works correctly."""
        manager = BackupManager()
        
        # Create backup
        zip_bytes, _ = manager.create_backup()
        
        # Extract and modify backup to corrupt checksum
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        try:
            temp_file.write(zip_bytes)
            temp_file.close()
            
            # Read and modify backup
            with zipfile.ZipFile(temp_file.name, 'r') as zf:
                files = [f for f in zf.namelist() if 'cashflow_backup' in f]
                backup_json = zf.read(files[0]).decode('utf-8')
                backup_data = json.loads(backup_json)
            
            # Corrupt the checksum
            backup_data['checksum'] = 'invalid_checksum_12345'
            
            # Create new ZIP with corrupted data
            corrupted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            try:
                with zipfile.ZipFile(corrupted_file.name, 'w') as zf:
                    zf.writestr('backup.json', json.dumps(backup_data, indent=2, sort_keys=True))
                
                with open(corrupted_file.name, 'rb') as f:
                    corrupted_bytes = f.read()
                
                # Validate - should fail
                is_valid, message, _ = manager.validate_backup(corrupted_bytes)
                
                assert is_valid is False
                assert "checksum" in message.lower()
            finally:
                Path(corrupted_file.name).unlink()
        finally:
            Path(temp_file.name).unlink()
