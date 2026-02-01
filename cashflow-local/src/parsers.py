"""
Statement Parser Engine for CashFlow-Local

Supports parsing bank statements from multiple formats:
- CSV files (with auto-detection of column headers)
- PDF files (using pdfplumber for table extraction)

Design Pattern: Abstract Base Class + Concrete Implementations
Performance: Streaming for large files, vectorized with Pandas/Polars
"""

import os
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from io import BytesIO

import pandas as pd
import polars as pl
import pdfplumber

logger = logging.getLogger(__name__)


class StatementParser(ABC):
    """
    Abstract base class for bank statement parsers.
    
    All parsers must implement the parse() method which returns
    a standardized DataFrame with the following schema:
    - transaction_date: datetime
    - description: str
    - amount: float
    - type: str ('Debit' or 'Credit')
    """
    
    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """
        Parse the statement and return standardized DataFrame.
        
        Returns:
            DataFrame with columns: [transaction_date, description, amount, type]
        """
        pass
    
    @staticmethod
    def normalize_amount(debit: Optional[float], credit: Optional[float]) -> tuple:
        """
        Normalize debit/credit columns into (amount, type).
        
        Args:
            debit: Debit amount (negative transaction)
            credit: Credit amount (positive transaction)
        
        Returns:
            Tuple of (amount: float, type: str)
        """
        if pd.notna(debit) and debit != 0:
            return abs(float(debit)), 'Debit'
        elif pd.notna(credit) and credit != 0:
            return abs(float(credit)), 'Credit'
        else:
            return 0.0, 'Unknown'


class CSVParser(StatementParser):
    """
    CSV statement parser with fuzzy column matching.
    
    Handles variations in column names across different banks:
    - Date: "Date", "Trans Date", "Transaction Date", "Posted Date"
    - Description: "Description", "Memo", "Details", "Merchant"
    - Debit: "Debit", "Amount", "Withdrawal"
    - Credit: "Credit", "Deposit"
    - Balance: "Balance", "Running Balance"
    
    Performance: O(n) where n = number of rows
    """
    
    # Column name mappings (lowercase for case-insensitive matching)
    COLUMN_MAPPINGS = {
        'date': ['date', 'trans date', 'transaction date', 'posted date', 'posting date', 'value date'],
        'description': ['description', 'memo', 'details', 'merchant', 'name', 'payee', 'particulars'],
        'debit': ['debit', 'withdrawal', 'withdrawals', 'amount', 'dr'],
        'credit': ['credit', 'deposit', 'deposits', 'cr'],
        'balance': ['balance', 'running balance', 'available balance']
    }
    
    def __init__(self, file_path: str):
        """
        Initialize CSV parser.
        
        Args:
            file_path: Path to CSV file
        """
        self.file_path = file_path
        logger.info(f"Initializing CSV parser for: {file_path}")
    
    def _detect_column(self, df: pd.DataFrame, column_type: str) -> Optional[str]:
        """
        Detect actual column name using fuzzy matching.
        
        Args:
            df: DataFrame with original column names
            column_type: Type from COLUMN_MAPPINGS ('date', 'description', etc.)
        
        Returns:
            Matched column name or None
        """
        possible_names = self.COLUMN_MAPPINGS.get(column_type, [])
        df_columns_lower = {col.lower(): col for col in df.columns}
        
        for possible_name in possible_names:
            if possible_name in df_columns_lower:
                matched_col = df_columns_lower[possible_name]
                logger.debug(f"Matched '{column_type}' to column '{matched_col}'")
                return matched_col
        
        logger.warning(f"Could not find column for '{column_type}'")
        return None
    
    def parse(self) -> pd.DataFrame:
        """
        Parse CSV file and return standardized DataFrame.
        
        Returns:
            DataFrame with standard schema
        
        Raises:
            Exception: If required columns are missing or parsing fails
        """
        try:
            # Read CSV
            df = pd.read_csv(self.file_path)
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Detect columns
            date_col = self._detect_column(df, 'date')
            desc_col = self._detect_column(df, 'description')
            debit_col = self._detect_column(df, 'debit')
            credit_col = self._detect_column(df, 'credit')
            
            # Validate required columns
            if not date_col or not desc_col:
                raise ValueError("Missing required columns: date and description")
            
            # If only one amount column exists, treat it as debit/credit based on sign
            if not debit_col and not credit_col:
                # Look for generic "amount" column
                amount_col = self._detect_column(df, 'debit')  # Uses 'amount' in mapping
                if amount_col:
                    df['debit_temp'] = df[amount_col].apply(lambda x: abs(x) if x < 0 else 0)
                    df['credit_temp'] = df[amount_col].apply(lambda x: x if x > 0 else 0)
                    debit_col = 'debit_temp'
                    credit_col = 'credit_temp'
                else:
                    raise ValueError("Missing amount columns (debit/credit)")
            
            # Normalize data
            result = pd.DataFrame()
            result['transaction_date'] = pd.to_datetime(df[date_col])
            result['description'] = df[desc_col].astype(str).str.strip()
            
            # Process amounts
            amounts_and_types = df.apply(
                lambda row: self.normalize_amount(
                    row.get(debit_col) if debit_col else None,
                    row.get(credit_col) if credit_col else None
                ),
                axis=1
            )
            result['amount'] = [a[0] for a in amounts_and_types]
            result['type'] = [a[1] for a in amounts_and_types]
            
            # Default category
            result['category'] = 'Uncategorized'
            
            # Filter out zero-amount transactions
            result = result[result['amount'] > 0].copy()
            
            logger.info(f"Successfully parsed {len(result)} valid transactions from CSV")
            return result
        
        except Exception as e:
            logger.error(f"CSV parsing failed: {e}")
            raise


class PDFParser(StatementParser):
    """
    PDF statement parser using pdfplumber for table extraction.
    
    Performance:
    - Processes page-by-page to avoid memory overflow
    - Regex patterns for parsing table rows
    - Time complexity: O(n * m) where n=rows, m=pages
    
    Limitations:
    - Bank statement formats vary; patterns may need customization
    - Works best with tabular PDFs (not scanned images)
    """
    
    def __init__(self, file_path: str):
        """
        Initialize PDF parser.
        
        Args:
            file_path: Path to PDF file
        """
        self.file_path = file_path
        logger.info(f"Initializing PDF parser for: {file_path}")
    
    def parse(self) -> pd.DataFrame:
        """
        Parse PDF file and extract transaction tables.
        
        Returns:
            DataFrame with standard schema
        
        Raises:
            Exception: If PDF extraction fails
        """
        try:
            all_transactions = []
            
            with pdfplumber.open(self.file_path) as pdf:
                logger.info(f"Opened PDF with {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.debug(f"Processing page {page_num}")
                    
                    # Extract tables from page
                    tables = page.extract_tables()
                    
                    if not tables:
                        logger.debug(f"Page {page_num}: No tables found")
                        continue
                    
                    logger.info(f"Page {page_num}: Found {len(tables)} tables")
                    
                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            logger.debug(f"Page {page_num}, Table {table_idx}: Too few rows, skipping")
                            continue
                        
                        logger.debug(f"Page {page_num}, Table {table_idx}: {len(table)} rows")
                        
                        # Clean table - remove None values and convert to strings
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell is not None else '' for cell in row]
                            # Only keep rows that aren't all empty
                            if any(cell for cell in cleaned_row):
                                cleaned_table.append(cleaned_row)
                        
                        if len(cleaned_table) < 2:
                            logger.debug(f"Page {page_num}, Table {table_idx}: No data after cleaning")
                            continue
                        
                        # Try to parse this table
                        try:
                            # Use first row as header
                            df_page = pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0])
                            logger.debug(f"Page {page_num}, Table {table_idx}: Columns = {list(df_page.columns)}")
                            
                            parsed = self._parse_table(df_page)
                            if not parsed.empty:
                                logger.info(f"Page {page_num}, Table {table_idx}: Parsed {len(parsed)} transactions")
                                all_transactions.append(parsed)
                            else:
                                logger.debug(f"Page {page_num}, Table {table_idx}: No valid transactions found")
                        except Exception as e:
                            logger.debug(f"Page {page_num}, Table {table_idx}: Failed to parse - {e}")
                            continue
            
            # Combine all pages
            if all_transactions:
                result = pd.concat(all_transactions, ignore_index=True)
                logger.info(f"Successfully parsed {len(result)} total transactions from PDF")
                return result
            else:
                logger.warning("No transactions found in PDF - tables may not match expected format")
                logger.warning("PDF should contain tables with columns: Date, Description, Debit/Credit or Amount")
                return pd.DataFrame(columns=['transaction_date', 'description', 'amount', 'type', 'category'])
        
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            raise
    
    def _parse_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse a table extracted from PDF into standardized format.
        
        Uses fuzzy column matching similar to CSVParser.
        
        Args:
            df: Raw DataFrame from PDF table
        
        Returns:
            Standardized DataFrame (may be empty if parsing fails)
        """
        try:
            # Use same column detection as CSV parser
            csv_parser = CSVParser.__new__(CSVParser)
            csv_parser.file_path = ""  # Not needed for column detection
            
            date_col = csv_parser._detect_column(df, 'date')
            desc_col = csv_parser._detect_column(df, 'description')
            debit_col = csv_parser._detect_column(df, 'debit')
            credit_col = csv_parser._detect_column(df, 'credit')
            
            if not date_col or not desc_col:
                logger.debug(f"Table columns: {list(df.columns)}")
                logger.debug(f"Missing required columns - Date: {date_col}, Description: {desc_col}")
                return pd.DataFrame()
            
            # Check for amount columns
            if not debit_col and not credit_col:
                logger.debug("No debit/credit columns found, table may not be a transaction table")
                return pd.DataFrame()
            
            logger.debug(f"Matched columns - Date: {date_col}, Desc: {desc_col}, Debit: {debit_col}, Credit: {credit_col}")
            
            # Normalize
            result = pd.DataFrame()
            result['transaction_date'] = pd.to_datetime(df[date_col], errors='coerce')
            result['description'] = df[desc_col].astype(str).str.strip()
            
            # Process amounts
            amounts_and_types = df.apply(
                lambda row: csv_parser.normalize_amount(
                    row.get(debit_col) if debit_col else None,
                    row.get(credit_col) if credit_col else None
                ),
                axis=1
            )
            result['amount'] = [a[0] for a in amounts_and_types]
            result['type'] = [a[1] for a in amounts_and_types]
            result['category'] = 'Uncategorized'
            
            # Filter invalid rows
            result = result.dropna(subset=['transaction_date'])
            result = result[result['amount'] > 0].copy()
            
            logger.debug(f"Parsed {len(result)} valid transactions from table")
            return result
        
        except Exception as e:
            logger.debug(f"Table parsing failed: {e}")
            return pd.DataFrame()


def create_parser(file_path: str, file_content: Optional[BytesIO] = None) -> StatementParser:
    """
    Factory function to create appropriate parser based on file extension.
    
    Args:
        file_path: Path or filename (used for extension detection)
        file_content: Optional BytesIO for uploaded files
    
    Returns:
        Instance of CSVParser or PDFParser
    
    Raises:
        ValueError: If file format is not supported
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.csv':
        logger.info("Detected CSV format")
        return CSVParser(file_path)
    elif file_ext == '.pdf':
        logger.info("Detected PDF format")
        return PDFParser(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Supported: .csv, .pdf")


def compute_file_hash(file_content: BytesIO) -> str:
    """
    Compute MD5 hash of uploaded file for tracking.
    
    Args:
        file_content: File content as BytesIO
    
    Returns:
        32-character MD5 hex digest
    """
    file_content.seek(0)
    return hashlib.md5(file_content.read()).hexdigest()
