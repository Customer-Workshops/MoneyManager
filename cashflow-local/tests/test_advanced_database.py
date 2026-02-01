"""
Tests for advanced database features (tags, saved searches).
"""

import pytest
import tempfile
import os
import json
from src.database import DatabaseManager


class TestAdvancedDatabaseFeatures:
    """Test suite for tags and saved searches."""
    
    @pytest.fixture
    def db_manager(self):
        """Create a test database manager with temporary database."""
        # Create temporary database file
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.duckdb')
        temp_db.close()
        
        # Set environment variable
        os.environ['DB_PATH'] = temp_db.name
        
        # Create new instance (will use temp DB)
        # Need to reset singleton
        DatabaseManager._instance = None
        DatabaseManager._connection = None
        manager = DatabaseManager()
        
        yield manager
        
        # Cleanup
        manager.close()
        os.unlink(temp_db.name)
        DatabaseManager._instance = None
        DatabaseManager._connection = None
    
    def test_add_tag(self, db_manager):
        """Test adding a new tag."""
        tag_id = db_manager.add_tag("Important", "#FF0000")
        assert tag_id is not None
        assert isinstance(tag_id, int)
    
    def test_get_all_tags(self, db_manager):
        """Test retrieving all tags."""
        # Add some tags
        db_manager.add_tag("Work", "#0000FF")
        db_manager.add_tag("Personal", "#00FF00")
        
        tags = db_manager.get_all_tags()
        assert len(tags) == 2
        assert all('id' in tag and 'name' in tag and 'color' in tag for tag in tags)
    
    def test_tag_transaction(self, db_manager):
        """Test associating a tag with a transaction."""
        # First insert a transaction
        transaction_data = [{
            'hash': 'test_hash_123',
            'transaction_date': '2024-01-15',
            'description': 'Test Transaction',
            'amount': 100.00,
            'type': 'Debit',
            'category': 'Test',
            'source_file_hash': 'file_hash_123'
        }]
        db_manager.execute_insert('transactions', transaction_data)
        
        # Add a tag
        tag_id = db_manager.add_tag("TestTag", "#123456")
        
        # Tag the transaction
        result = db_manager.tag_transaction(1, tag_id)
        assert result is True
    
    def test_get_transaction_tags(self, db_manager):
        """Test retrieving tags for a transaction."""
        # Insert transaction
        transaction_data = [{
            'hash': 'test_hash_456',
            'transaction_date': '2024-01-16',
            'description': 'Tagged Transaction',
            'amount': 50.00,
            'type': 'Credit',
            'category': 'Income',
            'source_file_hash': 'file_hash_456'
        }]
        db_manager.execute_insert('transactions', transaction_data)
        
        # Add tags
        tag1_id = db_manager.add_tag("Tag1", "#111111")
        tag2_id = db_manager.add_tag("Tag2", "#222222")
        
        # Tag the transaction
        db_manager.tag_transaction(1, tag1_id)
        db_manager.tag_transaction(1, tag2_id)
        
        # Get tags
        tags = db_manager.get_transaction_tags(1)
        assert len(tags) == 2
        assert "Tag1" in tags
        assert "Tag2" in tags
    
    def test_save_search(self, db_manager):
        """Test saving a search configuration."""
        filter_config = {
            "categories": ["Coffee", "Dining"],
            "min_amount": 5.0,
            "max_amount": 50.0
        }
        
        result = db_manager.save_search("Coffee Expenses", json.dumps(filter_config))
        assert result is True
    
    def test_get_saved_searches(self, db_manager):
        """Test retrieving saved searches."""
        # Save some searches
        config1 = {"category": "Coffee"}
        config2 = {"category": "Dining"}
        
        db_manager.save_search("Coffee Search", json.dumps(config1))
        db_manager.save_search("Dining Search", json.dumps(config2))
        
        searches = db_manager.get_saved_searches()
        assert len(searches) == 2
        assert all('id' in s and 'name' in s and 'filter_config' in s for s in searches)
    
    def test_duplicate_tag_name(self, db_manager):
        """Test that duplicate tag names are handled."""
        # Add first tag
        tag1_id = db_manager.add_tag("Duplicate", "#111111")
        assert tag1_id is not None
        
        # Try to add duplicate - should fail or return None
        tag2_id = db_manager.add_tag("Duplicate", "#222222")
        assert tag2_id is None  # Expecting constraint violation
    
    def test_tag_transaction_invalid_ids(self, db_manager):
        """Test tagging with invalid transaction or tag IDs."""
        # Try to tag non-existent transaction/tag
        result = db_manager.tag_transaction(99999, 99999)
        # Should fail gracefully
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
