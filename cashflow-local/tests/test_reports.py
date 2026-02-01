"""
Tests for report generation functionality.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import json

from src.reports import ReportGenerator


class TestReportGenerator:
    """Test suite for report generation."""
    
    @pytest.fixture
    def report_gen(self):
        """Create a report generator instance."""
        return ReportGenerator()
    
    def test_report_generator_initialization(self, report_gen):
        """Test that ReportGenerator initializes correctly."""
        assert report_gen is not None
        assert report_gen.styles is not None
        assert 'CustomTitle' in report_gen.styles
        assert 'CustomSubtitle' in report_gen.styles
        assert 'SectionHeader' in report_gen.styles
    
    def test_get_transactions_data(self, report_gen):
        """Test fetching transaction data from database."""
        # Test basic fetch (no filters)
        df = report_gen.get_transactions_data()
        assert isinstance(df, pd.DataFrame)
        
        # Test with date range filter
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        df_filtered = report_gen.get_transactions_data(start_date=start_date, end_date=end_date)
        assert isinstance(df_filtered, pd.DataFrame)
    
    def test_generate_monthly_statement_pdf(self, report_gen):
        """Test PDF generation for monthly statement."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        buffer = report_gen.generate_monthly_statement_pdf(start_date, end_date)
        
        assert isinstance(buffer, BytesIO)
        assert buffer.tell() == 0  # Should be at start
        content = buffer.read()
        assert len(content) > 0  # Should have content
        assert content[:4] == b'%PDF'  # PDF magic number
    
    def test_generate_tax_report_pdf(self, report_gen):
        """Test PDF generation for tax report."""
        # Use current tax year
        current_year = datetime.now().year
        start_date = datetime(current_year, 1, 1)
        end_date = datetime(current_year, 12, 31)
        
        buffer = report_gen.generate_tax_report_pdf(start_date, end_date)
        
        assert isinstance(buffer, BytesIO)
        content = buffer.read()
        assert len(content) > 0
        assert content[:4] == b'%PDF'
    
    def test_generate_category_report_pdf(self, report_gen):
        """Test PDF generation for category report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        category = "Food & Dining"
        
        buffer = report_gen.generate_category_report_pdf(start_date, end_date, category)
        
        assert isinstance(buffer, BytesIO)
        content = buffer.read()
        assert len(content) > 0
        assert content[:4] == b'%PDF'
    
    def test_generate_transaction_listing_pdf(self, report_gen):
        """Test PDF generation for transaction listing."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Test with no filters
        buffer = report_gen.generate_transaction_listing_pdf()
        assert isinstance(buffer, BytesIO)
        content = buffer.read()
        assert len(content) > 0
        assert content[:4] == b'%PDF'
        
        # Test with filters
        buffer = report_gen.generate_transaction_listing_pdf(
            start_date=start_date,
            end_date=end_date,
            category="Food & Dining",
            transaction_type="Debit"
        )
        assert isinstance(buffer, BytesIO)
    
    def test_export_to_excel(self, report_gen):
        """Test Excel export functionality."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        buffer = report_gen.export_to_excel(start_date=start_date, end_date=end_date)
        
        assert isinstance(buffer, BytesIO)
        assert buffer.tell() == 0  # Should be at start
        content = buffer.read()
        assert len(content) > 0
        # Excel files start with PK (zip format)
        assert content[:2] == b'PK'
    
    def test_export_to_csv(self, report_gen):
        """Test CSV export functionality."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        buffer = report_gen.export_to_csv(start_date=start_date, end_date=end_date)
        
        assert isinstance(buffer, BytesIO)
        content = buffer.read().decode('utf-8')
        assert len(content) > 0
        # CSV should have headers
        assert 'transaction_date' in content or 'description' in content
    
    def test_export_to_json(self, report_gen):
        """Test JSON export functionality."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        buffer = report_gen.export_to_json(start_date=start_date, end_date=end_date)
        
        assert isinstance(buffer, BytesIO)
        content = buffer.read().decode('utf-8')
        assert len(content) > 0
        
        # Should be valid JSON
        data = json.loads(content)
        assert isinstance(data, list)
    
    def test_export_with_category_filter(self, report_gen):
        """Test exports with category filter."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        category = "Food & Dining"
        
        # Test CSV with category filter
        buffer = report_gen.export_to_csv(
            start_date=start_date,
            end_date=end_date,
            category=category
        )
        assert isinstance(buffer, BytesIO)
        
        # Test JSON with category filter
        buffer = report_gen.export_to_json(
            start_date=start_date,
            end_date=end_date,
            category=category
        )
        assert isinstance(buffer, BytesIO)
    
    def test_export_with_type_filter(self, report_gen):
        """Test exports with transaction type filter."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Test with Credit transactions
        buffer = report_gen.export_to_json(
            start_date=start_date,
            end_date=end_date,
            transaction_type="Credit"
        )
        assert isinstance(buffer, BytesIO)
        
        # Test with Debit transactions
        buffer = report_gen.export_to_json(
            start_date=start_date,
            end_date=end_date,
            transaction_type="Debit"
        )
        assert isinstance(buffer, BytesIO)
