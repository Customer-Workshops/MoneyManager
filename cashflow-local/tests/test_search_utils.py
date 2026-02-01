"""
Tests for search utilities and advanced filtering.
"""

import pytest
from src.search_utils import fuzzy_match, regex_search, filter_by_search


class TestSearchUtils:
    """Test suite for search utilities."""
    
    def test_fuzzy_match_exact(self):
        """Test fuzzy match with exact substring."""
        assert fuzzy_match("Starbucks Coffee", "Starbucks", 0.6) is True
        assert fuzzy_match("AMAZON PURCHASE", "amazon", 0.6) is True
    
    def test_fuzzy_match_typos(self):
        """Test fuzzy match handles typos."""
        # Common typos should match
        assert fuzzy_match("Starbucks", "Starbuck", 0.8) is True
        assert fuzzy_match("Amazon", "Amzon", 0.8) is True
        assert fuzzy_match("Restaurant", "Resturant", 0.7) is True
    
    def test_fuzzy_match_no_match(self):
        """Test fuzzy match with completely different strings."""
        assert fuzzy_match("Starbucks", "Amazon", 0.6) is False
        assert fuzzy_match("Coffee Shop", "Electronics", 0.6) is False
    
    def test_fuzzy_match_empty_pattern(self):
        """Test fuzzy match with empty pattern."""
        assert fuzzy_match("Any Text", "", 0.6) is True
    
    def test_regex_search_valid(self):
        """Test regex search with valid patterns."""
        # Match currency amounts
        assert regex_search("Amount: $123.45", r"\$\d+\.\d+") is True
        assert regex_search("Total: $1,234.56", r"\$[\d,]+\.\d+") is True
        
        # Match dates
        assert regex_search("Date: 2024-01-15", r"\d{4}-\d{2}-\d{2}") is True
        
        # Match words
        assert regex_search("Starbucks Coffee", r"Star\w+") is True
    
    def test_regex_search_no_match(self):
        """Test regex search with non-matching patterns."""
        assert regex_search("No numbers here", r"\d+") is False
        assert regex_search("lowercase only", r"[A-Z]+") is False
    
    def test_regex_search_invalid_pattern(self):
        """Test regex search with invalid pattern falls back to substring."""
        # Invalid regex should fallback to substring search
        assert regex_search("Test String", "[invalid(") is False
        assert regex_search("Test invalid", "invalid") is True
    
    def test_filter_by_search_exact(self):
        """Test filtering transactions with exact search."""
        transactions = [
            {"id": 1, "description": "Starbucks Coffee", "amount": 5.50},
            {"id": 2, "description": "Amazon Purchase", "amount": 25.00},
            {"id": 3, "description": "Starbucks Latte", "amount": 6.00},
        ]
        
        result = filter_by_search(transactions, "Starbucks", "exact")
        assert len(result) == 2
        assert all("Starbucks" in txn["description"] for txn in result)
    
    def test_filter_by_search_fuzzy(self):
        """Test filtering transactions with fuzzy search."""
        transactions = [
            {"id": 1, "description": "Starbucks Coffee", "amount": 5.50},
            {"id": 2, "description": "Starbuck", "amount": 5.00},  # Typo
            {"id": 3, "description": "Amazon Purchase", "amount": 25.00},
        ]
        
        result = filter_by_search(transactions, "Starbucks", "fuzzy", fuzzy_threshold=0.7)
        assert len(result) >= 2  # Should match both "Starbucks" and "Starbuck"
    
    def test_filter_by_search_regex(self):
        """Test filtering transactions with regex search."""
        transactions = [
            {"id": 1, "description": "Payment to John123", "amount": 100.00},
            {"id": 2, "description": "Payment to Jane456", "amount": 200.00},
            {"id": 3, "description": "Cash Withdrawal", "amount": 50.00},
        ]
        
        result = filter_by_search(transactions, r"John\d+", "regex")
        assert len(result) == 1
        assert result[0]["id"] == 1
    
    def test_filter_by_search_empty_query(self):
        """Test filtering with empty search query returns all."""
        transactions = [
            {"id": 1, "description": "Transaction 1", "amount": 10.00},
            {"id": 2, "description": "Transaction 2", "amount": 20.00},
        ]
        
        result = filter_by_search(transactions, "", "exact")
        assert len(result) == len(transactions)
    
    def test_filter_by_search_empty_transactions(self):
        """Test filtering empty transaction list."""
        result = filter_by_search([], "anything", "exact")
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
