"""
Tests for categorization engine.
"""

import pytest
from src.categorization import CategoryEngine


class TestCategoryEngine:
    """Test suite for categorization engine."""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create a test category engine with custom rules path."""
        rules_path = tmp_path / "test_rules.json"
        engine = CategoryEngine(str(rules_path))
        return engine
    
    def test_categorize_transaction(self, engine):
        """Test single transaction categorization."""
        # Add a test rule
        engine.rules = [
            {"keyword": "starbucks", "category": "Coffee"}
        ]
        
        category = engine.categorize_transaction("STARBUCKS #1234")
        assert category == "Coffee", "Should match keyword case-insensitively"
        
        category = engine.categorize_transaction("UNKNOWN MERCHANT")
        assert category == "Uncategorized", "Should return Uncategorized for no match"
    
    def test_save_rule(self, engine):
        """Test saving a new rule."""
        success = engine.save_rule("test_keyword", "Test Category")
        assert success, "Rule should be saved successfully"
        assert len(engine.rules) > 0, "Rules list should contain the new rule"
        
        # Verify rule was added
        found = False
        for rule in engine.rules:
            if rule['keyword'] == "test_keyword" and rule['category'] == "Test Category":
                found = True
                break
        assert found, "New rule should be in rules list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
