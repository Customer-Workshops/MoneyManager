"""
Tests for enhanced parser functionality including:
- Multiple date format support
- Robust amount parsing
- Edge case handling
- Error messages
"""

import pytest
import pandas as pd
from datetime import datetime
from src.parsers import StatementParser, PDFParser, CSVParser
from pathlib import Path
import tempfile
import os


class TestAmountParsing:
    """Test enhanced amount parsing functionality."""
    
    def test_parse_comma_separated_amounts(self):
        """Test parsing amounts with comma separators."""
        assert StatementParser.parse_amount("1,234.56") == 1234.56
        assert StatementParser.parse_amount("1,23,456.78") == 123456.78
    
    def test_parse_currency_symbols(self):
        """Test parsing amounts with currency symbols."""
        assert StatementParser.parse_amount("₹1,234.56") == 1234.56
        assert StatementParser.parse_amount("$1,234.56") == 1234.56
        assert StatementParser.parse_amount("€1234.56") == 1234.56
    
    def test_parse_debit_indicators(self):
        """Test parsing amounts with debit/credit indicators."""
        assert StatementParser.parse_amount("1234.56 Dr") == 1234.56
        assert StatementParser.parse_amount("1234.56 CR") == 1234.56
        assert StatementParser.parse_amount("1234.56 dr") == 1234.56
    
    def test_parse_accounting_format(self):
        """Test parsing amounts in accounting format (parentheses for negative)."""
        assert StatementParser.parse_amount("(1234.56)") == -1234.56
        assert StatementParser.parse_amount("(500)") == -500.0
    
    def test_parse_empty_cells(self):
        """Test parsing empty/placeholder values."""
        assert StatementParser.parse_amount("--") is None
        assert StatementParser.parse_amount("-") is None
        assert StatementParser.parse_amount("") is None
        assert StatementParser.parse_amount("nan") is None
        assert StatementParser.parse_amount(None) is None
    
    def test_parse_no_decimals(self):
        """Test parsing amounts without decimal points."""
        assert StatementParser.parse_amount("500") == 500.0
        assert StatementParser.parse_amount("1000") == 1000.0
    
    def test_parse_invalid_amounts(self):
        """Test parsing invalid amount strings."""
        assert StatementParser.parse_amount("abc") is None
        assert StatementParser.parse_amount("12.34.56") is None


class TestDateParsing:
    """Test enhanced date parsing functionality."""
    
    def test_parse_dd_mm_yyyy_slash(self):
        """Test DD/MM/YYYY format."""
        date = StatementParser.parse_date("01/09/2025")
        assert date == datetime(2025, 9, 1)
    
    def test_parse_dd_mm_yyyy_dash(self):
        """Test DD-MM-YYYY format."""
        date = StatementParser.parse_date("01-09-2025")
        assert date == datetime(2025, 9, 1)
    
    def test_parse_dd_mmm_yyyy(self):
        """Test DD-MMM-YYYY format."""
        date = StatementParser.parse_date("01-Sep-2025")
        assert date == datetime(2025, 9, 1)
    
    def test_parse_yyyy_mm_dd(self):
        """Test YYYY-MM-DD format."""
        date = StatementParser.parse_date("2025-09-01")
        assert date == datetime(2025, 9, 1)
    
    def test_parse_dd_mmm_yyyy_space(self):
        """Test DD MMM YYYY format."""
        date = StatementParser.parse_date("01 Sep 2025")
        assert date == datetime(2025, 9, 1)
    
    def test_parse_dd_mm_yy(self):
        """Test DD/MM/YY format."""
        date = StatementParser.parse_date("01/09/25")
        assert date == datetime(2025, 9, 1)
    
    def test_parse_invalid_dates(self):
        """Test parsing invalid date strings."""
        assert StatementParser.parse_date("") is None
        assert StatementParser.parse_date(None) is None
        assert StatementParser.parse_date("invalid") is None
        assert StatementParser.parse_date("32/13/2025") is None


class TestNormalizeAmount:
    """Test amount normalization from debit/credit columns."""
    
    def test_normalize_with_debit(self):
        """Test normalization when debit column has value."""
        amount, type_ = StatementParser.normalize_amount("1234.56", None)
        assert amount == 1234.56
        assert type_ == 'Debit'
    
    def test_normalize_with_credit(self):
        """Test normalization when credit column has value."""
        amount, type_ = StatementParser.normalize_amount(None, "1234.56")
        assert amount == 1234.56
        assert type_ == 'Credit'
    
    def test_normalize_with_comma_separated(self):
        """Test normalization with comma-separated amounts."""
        amount, type_ = StatementParser.normalize_amount("1,234.56", None)
        assert amount == 1234.56
        assert type_ == 'Debit'
    
    def test_normalize_both_empty(self):
        """Test normalization when both columns are empty."""
        amount, type_ = StatementParser.normalize_amount(None, None)
        assert amount == 0.0
        assert type_ == 'Unknown'
    
    def test_normalize_with_currency_symbols(self):
        """Test normalization with currency symbols."""
        amount, type_ = StatementParser.normalize_amount("₹1,234.56", None)
        assert amount == 1234.56
        assert type_ == 'Debit'


class TestCSVParserErrors:
    """Test CSV parser error handling."""
    
    def test_file_not_found(self):
        """Test error when CSV file doesn't exist."""
        parser = CSVParser("/nonexistent/file.csv")
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse()
        assert "CSV file not found" in str(exc_info.value)
        assert "💡" in str(exc_info.value)
    
    def test_empty_csv(self):
        """Test error when CSV is empty."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,Description,Debit,Credit\n")  # Header only
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            with pytest.raises(ValueError) as exc_info:
                parser.parse()
            assert "empty" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)
    
    def test_missing_date_column(self):
        """Test error when date column is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Description,Debit,Credit\n")
            f.write("Test,100,0\n")
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            with pytest.raises(ValueError) as exc_info:
                parser.parse()
            assert "Missing required column: Date" in str(exc_info.value)
            assert "💡" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_missing_description_column(self):
        """Test error when description column is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,Debit,Credit\n")
            f.write("01/09/2025,100,0\n")
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            with pytest.raises(ValueError) as exc_info:
                parser.parse()
            assert "Missing required column: Description" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestPDFParserErrors:
    """Test PDF parser error handling."""
    
    def test_file_not_found(self):
        """Test error when PDF file doesn't exist."""
        parser = PDFParser("/nonexistent/file.pdf")
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse()
        assert "PDF file not found" in str(exc_info.value)
        assert "💡" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases in statement parsing."""
    
    def test_csv_with_all_zero_amounts(self):
        """Test CSV where all amounts are zero."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,Description,Debit,Credit\n")
            f.write("01/09/2025,Test1,0,0\n")
            f.write("02/09/2025,Test2,0,0\n")
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            with pytest.raises(ValueError) as exc_info:
                parser.parse()
            assert "0 valid transactions" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_csv_with_consistent_date_format(self):
        """Test CSV with transactions in consistent date format.
        
        Note: Pandas to_datetime with dayfirst=True works best with consistent formats.
        Mixed date formats in a single CSV may not parse correctly due to pandas limitations.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,Description,Debit,Credit\n")
            f.write("01/09/2025,Test1,100,0\n")
            f.write("02/09/2025,Test2,0,200\n")
            f.write("03/09/2025,Test3,150,0\n")
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            df = parser.parse()
            # All transactions should be parsed successfully
            assert len(df) == 3
            assert all(pd.notna(df['transaction_date']))
            # Verify correct date parsing (DD/MM/YYYY with dayfirst=True)
            assert df.iloc[0]['transaction_date'] == pd.Timestamp('2025-09-01')
        finally:
            os.unlink(temp_path)
    
    def test_csv_with_various_amount_formats(self):
        """Test CSV with different amount formats."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,Description,Debit,Credit\n")
            f.write("01/09/2025,Test1,1234.56,0\n")
            # Use quotes to handle comma in amount
            f.write('02/09/2025,Test2,0,"₹1,234.56"\n')
            f.write("03/09/2025,Test3,500,0\n")
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            df = parser.parse()
            assert len(df) == 3
            assert df.iloc[0]['amount'] == 1234.56
            assert df.iloc[1]['amount'] == 1234.56
            assert df.iloc[2]['amount'] == 500.0
        finally:
            os.unlink(temp_path)


class TestPerformance:
    """Test parser performance with edge cases."""
    
    def test_large_csv(self):
        """Test parsing a large CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,Description,Debit,Credit\n")
            # Generate 1000 transactions (starting from 1 to avoid zero amounts)
            for i in range(1, 1001):
                f.write(f"01/09/2025,Transaction {i},{i * 10},0\n")
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            df = parser.parse()
            assert len(df) == 1000
            assert df.iloc[0]['amount'] == 10.0  # First one (i=1) has 10
            assert df.iloc[1]['amount'] == 20.0
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
