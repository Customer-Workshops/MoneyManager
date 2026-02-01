"""
Tests for statement parsers.
"""

import pytest
import pandas as pd
from pathlib import Path
from src.parsers import CSVParser, create_parser


class TestCSVParser:
    """Test suite for CSV parser."""
    
    def test_csv_parser_initialization(self):
        """Test CSV parser can be initialized."""
        parser = CSVParser("test.csv")
        assert parser.file_path == "test.csv"
    
    def test_column_detection(self):
        """Test fuzzy column name matching."""
        parser = CSVParser("")
        
        # Create test DataFrame with various column names
        df = pd.DataFrame(columns=['Trans Date', 'Memo', 'Debit', 'Credit'])
        
        assert parser._detect_column(df, 'date') == 'Trans Date'
        assert parser._detect_column(df, 'description') == 'Memo'
        assert parser._detect_column(df, 'debit') == 'Debit'
        assert parser._detect_column(df, 'credit') == 'Credit'
    
    def test_csv_parsing_with_fixture(self):
        """Test parsing actual CSV fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_statement.csv"
        
        if not fixture_path.exists():
            pytest.skip("Sample CSV fixture not found")
        
        parser = CSVParser(str(fixture_path))
        df = parser.parse()
        
        assert not df.empty, "Parsed DataFrame should not be empty"
        assert 'transaction_date' in df.columns, "Should have transaction_date column"
        assert 'description' in df.columns, "Should have description column"
        assert 'amount' in df.columns, "Should have amount column"
        assert 'type' in df.columns, "Should have type column"
        assert 'category' in df.columns, "Should have category column"
        
        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(df['transaction_date']), "Date should be datetime"
        assert df['amount'].dtype == float, "Amount should be float"


class TestParserFactory:
    """Test suite for parser factory function."""
    
    def test_create_csv_parser(self):
        """Test factory creates CSV parser for .csv files."""
        parser = create_parser("test.csv")
        assert isinstance(parser, CSVParser)
    
    def test_unsupported_format(self):
        """Test factory raises error for unsupported formats."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            create_parser("test.txt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
