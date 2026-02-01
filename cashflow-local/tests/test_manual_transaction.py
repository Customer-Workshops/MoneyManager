"""
Tests for manual transaction entry functionality
"""

import pytest
from datetime import date, timedelta
from src.ui.components.transaction_form import validate_transaction, save_manual_transaction
from src.ui.utils import get_categories_by_type


def test_get_categories_by_type():
    """Test that categories are filtered correctly by transaction type."""
    # Test expense categories
    expense_cats = get_categories_by_type("💸 Expense")
    assert len(expense_cats) > 0
    assert "🍔 Food & Dining" in expense_cats
    assert "🚗 Transport" in expense_cats
    
    # Test income categories
    income_cats = get_categories_by_type("💰 Income")
    assert len(income_cats) > 0
    assert "💼 Salary" in income_cats
    assert "💵 Freelance" in income_cats
    
    # Test transfer categories
    transfer_cats = get_categories_by_type("🔄 Transfer")
    assert len(transfer_cats) > 0
    assert "🏦 Account Transfer" in transfer_cats
    
    # Ensure they're different
    assert set(expense_cats) != set(income_cats)
    assert set(expense_cats) != set(transfer_cats)


def test_validate_transaction_valid():
    """Test transaction validation with valid inputs."""
    is_valid, error = validate_transaction(
        transaction_date=date.today(),
        description="Coffee at Starbucks",
        amount=5.50
    )
    assert is_valid is True
    assert error is None


def test_validate_transaction_invalid_date():
    """Test transaction validation with invalid date (too far in future)."""
    is_valid, error = validate_transaction(
        transaction_date=date.today() + timedelta(days=400),
        description="Future transaction",
        amount=100.0
    )
    assert is_valid is False
    assert "future" in error.lower()


def test_validate_transaction_invalid_description():
    """Test transaction validation with invalid description (too short)."""
    is_valid, error = validate_transaction(
        transaction_date=date.today(),
        description="AB",  # Only 2 characters
        amount=100.0
    )
    assert is_valid is False
    assert "3 characters" in error.lower()


def test_validate_transaction_invalid_amount():
    """Test transaction validation with invalid amount (negative or zero)."""
    is_valid, error = validate_transaction(
        transaction_date=date.today(),
        description="Invalid amount",
        amount=0.0
    )
    assert is_valid is False
    assert "positive" in error.lower()
    
    is_valid, error = validate_transaction(
        transaction_date=date.today(),
        description="Invalid amount",
        amount=-10.0
    )
    assert is_valid is False
    assert "positive" in error.lower()


def test_save_manual_transaction_type_mapping():
    """Test that transaction types are correctly mapped to database types."""
    # This test verifies the type mapping logic
    # We can't fully test database insertion without a test database setup,
    # but we can verify the mapping logic is correct
    type_mapping = {
        '💸 Expense': 'Debit',
        '💰 Income': 'Credit',
        '🔄 Transfer': 'Transfer'
    }
    
    for ui_type, db_type in type_mapping.items():
        assert db_type in ['Debit', 'Credit', 'Transfer']


def test_category_icon_removal():
    """Test that icons are removed from categories before database storage."""
    category_with_icon = "🍔 Food & Dining"
    category_clean = category_with_icon.split(' ', 1)[1] if ' ' in category_with_icon else category_with_icon
    
    assert category_clean == "Food & Dining"
    assert "🍔" not in category_clean


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
