"""
Tests for deduplication engine.
"""

import pytest
import pandas as pd
from datetime import datetime
from src.deduplication import generate_hash, add_hashes_to_dataframe, insert_transactions
from src.database import DatabaseManager


class TestDeduplication:
    """Test suite for deduplication functionality."""
    
    def test_hash_generation_consistency(self):
        """Test that same inputs produce same hash."""
        date = datetime(2026, 1, 15)
        description = "STARBUCKS #1234"
        amount = 5.50
        
        hash1 = generate_hash(date, description, amount)
        hash2 = generate_hash(date, description, amount)
        
        assert hash1 == hash2, "Hashes should be identical for same inputs"
        assert len(hash1) == 32, "MD5 hash should be 32 characters"
    
    def test_hash_case_insensitive(self):
        """Test that description case doesn't affect hash."""
        date = datetime(2026, 1, 15)
        amount = 5.50
        
        hash1 = generate_hash(date, "Starbucks", amount)
        hash2 = generate_hash(date, "STARBUCKS", amount)
        hash3 = generate_hash(date, "starbucks", amount)
        
        assert hash1 == hash2 == hash3, "Hashes should be case-insensitive"
    
    def test_add_hashes_to_dataframe(self):
        """Test adding hashes to DataFrame."""
        df = pd.DataFrame({
            'transaction_date': [datetime(2026, 1, 1), datetime(2026, 1, 2)],
            'description': ['Purchase A', 'Purchase B'],
            'amount': [10.0, 20.0]
        })
        
        result = add_hashes_to_dataframe(df)
        
        assert 'hash' in result.columns, "Hash column should be added"
        assert len(result) == 2, "Row count should remain same"
        assert result['hash'].nunique() == 2, "Hashes should be unique"
    
    def test_duplicate_detection_logic(self):
        """Test that duplicate transactions are detected."""
        # Note: This test requires database setup
        # For now, we test the hash generation which is the core logic
        
        df = pd.DataFrame({
            'transaction_date': [datetime(2026, 1, 1), datetime(2026, 1, 1)],
            'description': ['Same Transaction', 'Same Transaction'],
            'amount': [10.0, 10.0]
        })
        
        df = add_hashes_to_dataframe(df)
        
        # Both rows should have identical hashes
        assert df['hash'].iloc[0] == df['hash'].iloc[1], "Duplicate transactions should have same hash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
