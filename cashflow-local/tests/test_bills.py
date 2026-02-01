"""
Tests for bill management functionality.
"""

import pytest
from datetime import datetime, timedelta
from src.bills import BillManager


class TestBillManager:
    """Test suite for bill management functionality."""
    
    def test_bill_types_defined(self):
        """Test that bill types are properly defined."""
        assert len(BillManager.BILL_TYPES) > 0
        assert "Rent" in BillManager.BILL_TYPES
        assert "Electricity" in BillManager.BILL_TYPES
        assert "Credit Card" in BillManager.BILL_TYPES
    
    def test_recurrence_types_defined(self):
        """Test that recurrence types are properly defined."""
        assert len(BillManager.RECURRENCE_TYPES) > 0
        assert "Monthly" in BillManager.RECURRENCE_TYPES
        assert "Quarterly" in BillManager.RECURRENCE_TYPES
        assert "Yearly" in BillManager.RECURRENCE_TYPES
    
    def test_calculate_next_due_date_monthly(self):
        """Test calculation of next due date for monthly bills."""
        current_date = datetime(2026, 1, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "Monthly")
        
        assert next_date.year == 2026
        assert next_date.month == 2
        assert next_date.day == 15
    
    def test_calculate_next_due_date_monthly_year_wrap(self):
        """Test monthly recurrence across year boundary."""
        current_date = datetime(2025, 12, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "Monthly")
        
        assert next_date.year == 2026
        assert next_date.month == 1
        assert next_date.day == 15
    
    def test_calculate_next_due_date_quarterly(self):
        """Test calculation of next due date for quarterly bills."""
        current_date = datetime(2026, 1, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "Quarterly")
        
        assert next_date.year == 2026
        assert next_date.month == 4
        assert next_date.day == 15
    
    def test_calculate_next_due_date_quarterly_year_wrap(self):
        """Test quarterly recurrence across year boundary."""
        current_date = datetime(2025, 11, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "Quarterly")
        
        assert next_date.year == 2026
        assert next_date.month == 2
        assert next_date.day == 15
    
    def test_calculate_next_due_date_half_yearly(self):
        """Test calculation of next due date for half-yearly bills."""
        current_date = datetime(2026, 1, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "Half-yearly")
        
        assert next_date.year == 2026
        assert next_date.month == 7
        assert next_date.day == 15
    
    def test_calculate_next_due_date_yearly(self):
        """Test calculation of next due date for yearly bills."""
        current_date = datetime(2026, 1, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "Yearly")
        
        assert next_date.year == 2027
        assert next_date.month == 1
        assert next_date.day == 15
    
    def test_calculate_next_due_date_one_time(self):
        """Test that one-time bills don't change due date."""
        current_date = datetime(2026, 1, 15).date()
        next_date = BillManager._calculate_next_due_date(current_date, "One-time")
        
        assert next_date.year == 2026
        assert next_date.month == 1
        assert next_date.day == 15
    
    def test_calculate_next_due_date_with_datetime(self):
        """Test that function handles datetime objects correctly."""
        current_datetime = datetime(2026, 1, 15, 10, 30, 0)
        next_date = BillManager._calculate_next_due_date(current_datetime, "Monthly")
        
        assert next_date.year == 2026
        assert next_date.month == 2
        assert next_date.day == 15
    
    def test_status_types_defined(self):
        """Test that status types are properly defined."""
        assert len(BillManager.STATUS_TYPES) > 0
        assert "pending" in BillManager.STATUS_TYPES
        assert "paid" in BillManager.STATUS_TYPES
        assert "overdue" in BillManager.STATUS_TYPES


# Note: Integration tests that require database access should be run separately
# with proper database setup and teardown

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
