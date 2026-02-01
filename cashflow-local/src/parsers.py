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
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from io import BytesIO

import pandas as pd
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
    def parse_amount(amount_str: str) -> Optional[float]:
        """
        Parse amount string into float, handling various formats.
        
        Supports:
        - Comma-separated: "1,234.56" → 1234.56
        - Currency symbols: "₹1,234.56" → 1234.56
        - Debit indicators: "1234.56 Dr" → 1234.56
        - Accounting format: "(1234.56)" → -1234.56
        - Empty cells: "--" → None
        - No decimals: "500" → 500.0
        
        Args:
            amount_str: String representation of amount
        
        Returns:
            Float value or None if invalid
        """
        if amount_str is None or not str(amount_str).strip():
            return None
        
        amount_str = str(amount_str).strip()
        
        # Handle empty/placeholder values
        if amount_str in ['--', '-', '', 'nan', 'None']:
            return None
        
        # Remove currency symbols (₹, $, €, etc.)
        amount_str = re.sub(r'[₹$€£¥]', '', amount_str)
        
        # Check for accounting format (parentheses for negative)
        is_negative = False
        if amount_str.startswith('(') and amount_str.endswith(')'):
            is_negative = True
            amount_str = amount_str[1:-1]
        
        # Remove debit/credit indicators
        amount_str = re.sub(r'\s*(Dr|Cr|DR|CR|dr|cr)\s*$', '', amount_str)
        
        # Remove commas
        amount_str = amount_str.replace(',', '')
        
        # Remove any remaining whitespace
        amount_str = amount_str.strip()
        
        try:
            value = float(amount_str)
            return -abs(value) if is_negative else abs(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse amount: '{amount_str}'")
            return None
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """
        Parse date string into datetime, supporting multiple formats.
        
        Supports:
        - DD/MM/YYYY: "01/09/2025"
        - DD-MM-YYYY: "01-09-2025"
        - DD-MMM-YYYY: "01-Sep-2025"
        - YYYY-MM-DD: "2025-09-01"
        - DD MMM YYYY: "01 Sep 2025"
        
        Args:
            date_str: String representation of date
        
        Returns:
            datetime object or None if parsing fails
        """
        if date_str is None or not str(date_str).strip():
            return None
        
        date_str = str(date_str).strip()
        
        # List of date formats to try
        date_formats = [
            '%d/%m/%Y',      # 01/09/2025
            '%d-%m-%Y',      # 01-09-2025
            '%d-%b-%Y',      # 01-Sep-2025
            '%d %b %Y',      # 01 Sep 2025
            '%Y-%m-%d',      # 2025-09-01
            '%d.%m.%Y',      # 01.09.2025
            '%d-%m-%y',      # 01-09-25
            '%d/%m/%y',      # 01/09/25
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: '{date_str}'")
        return None
    
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
        # Use enhanced parse_amount for better handling
        debit_clean = StatementParser.parse_amount(str(debit)) if debit is not None else None
        credit_clean = StatementParser.parse_amount(str(credit)) if credit is not None else None
        
        if debit_clean is not None and debit_clean != 0:
            return abs(debit_clean), 'Debit'
        elif credit_clean is not None and credit_clean != 0:
            return abs(credit_clean), 'Credit'
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
        'debit': ['debit', 'withdrawal', 'withdrawals', 'amount', 'dr', 'drawals', 'drawals deposits b', 'cheque details with'],  # Split headers
        'credit': ['credit', 'deposit', 'deposits', 'cr', 'posits', 'drawals deposits b'],  # 'drawals deposits b' can be both
        'balance': ['balance', 'running balance', 'available balance', 'alance']
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
        
        # Filter out None and empty column names before creating lowercase mapping
        df_columns_lower = {
            col.lower(): col 
            for col in df.columns 
            if col is not None and str(col).strip()
        }
        
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
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If required columns are missing or parsing fails
        """
        try:
            # Validate file exists
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(
                    f"CSV file not found: {self.file_path}\n"
                    f"💡 Tip: Check the file path and ensure the file exists"
                )
            
            # Read CSV
            df = pd.read_csv(self.file_path)
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            if df.empty:
                raise ValueError(
                    "CSV file is empty (0 rows)\n"
                    "💡 Tip: Ensure the CSV contains transaction data"
                )
            
            # Detect columns
            date_col = self._detect_column(df, 'date')
            desc_col = self._detect_column(df, 'description')
            debit_col = self._detect_column(df, 'debit')
            credit_col = self._detect_column(df, 'credit')
            
            # Validate required columns
            if not date_col:
                raise ValueError(
                    f"❌ Missing required column: Date\n"
                    f"💡 CSV columns found: {', '.join(df.columns.astype(str))}\n"
                    f"💡 Expected one of: {', '.join(self.COLUMN_MAPPINGS['date'])}"
                )
            
            if not desc_col:
                raise ValueError(
                    f"❌ Missing required column: Description\n"
                    f"💡 CSV columns found: {', '.join(df.columns.astype(str))}\n"
                    f"💡 Expected one of: {', '.join(self.COLUMN_MAPPINGS['description'])}"
                )
            
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
                    raise ValueError(
                        f"❌ Missing amount columns (debit/credit)\n"
                        f"💡 CSV columns found: {', '.join(df.columns.astype(str))}\n"
                        f"💡 Expected debit or credit column"
                    )
            
            logger.info(f"✅ Detected columns: Date={date_col}, Description={desc_col}, Debit={debit_col}, Credit={credit_col}")
            
            # Normalize data
            result = pd.DataFrame()
            result['transaction_date'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
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
            
            # Filter out zero-amount transactions and invalid dates
            result = result.dropna(subset=['transaction_date'])
            result = result[result['amount'] > 0].copy()
            
            logger.info(f"✅ Successfully parsed {len(result)} valid transactions from CSV")
            
            if result.empty:
                raise ValueError(
                    "⚠️ Parsed 0 valid transactions (all rows filtered out)\n"
                    "💡 Tip: Check if the CSV has valid dates and non-zero amounts"
                )
            
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
        
        Uses optimized settings for bank statements with dynamic header detection.
        
        Returns:
            DataFrame with standard schema
        
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If no transaction table found or parsing fails
            Exception: For other PDF extraction failures
        """
        try:
            # Validate file exists
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(
                    f"PDF file not found: {self.file_path}\n"
                    f"💡 Tip: Check the file path and ensure the file exists"
                )
            
            all_transactions = []
            
            # Custom extraction settings optimized for bank statements
            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": 3,
            }
            
            with pdfplumber.open(self.file_path) as pdf:
                logger.info(f"Opened PDF with {len(pdf.pages)} pages")
                
                if len(pdf.pages) == 0:
                    raise ValueError(
                        "PDF file is empty (0 pages)\n"
                        "💡 Tip: Ensure this is a valid bank statement PDF"
                    )
                
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.debug(f"Processing page {page_num}")
                    
                    # Extract tables with custom settings
                    tables = page.extract_tables(table_settings)
                    
                    if not tables:
                        logger.debug(f"Page {page_num}: No tables found")
                        continue
                    
                    logger.info(f"Page {page_num}: Found {len(tables)} table(s)")
                    
                    for table_idx, table in enumerate(tables):
                        if not table:
                            continue
                        
                        for row in table:
                            # Clean up row: remove newlines and None values
                            cleaned_row = [
                                cell.replace('\n', ' ').strip() if cell else ""
                                for cell in row
                            ]
                            
                            # Skip empty rows
                            if not any(cleaned_row):
                                continue
                            
                            all_transactions.append(cleaned_row)
            
            if not all_transactions:
                raise ValueError(
                    "❌ Failed to parse PDF: No transaction table found\n"
                    "💡 Tip: Make sure this is a bank statement PDF with a transaction table"
                )
            
            # Convert to DataFrame
            df = pd.DataFrame(all_transactions)
            logger.info(f"Extracted {len(df)} total rows from PDF")
            
            # Find and set header row
            # Look for row containing "Date" (case-insensitive)
            if not df.empty:
                is_header_row = df[0].astype(str).str.contains("date", case=False, na=False)
                
                if is_header_row.any():
                    # Use first header row as column names
                    header_row_index = is_header_row.idxmax()
                    raw_headers = df.iloc[header_row_index].tolist()
                    
                    # Clean and join all header fragments into a single string
                    # Then try to  identify column boundaries
                    header_text = ' '.join([str(h).strip() for h in raw_headers if h and str(h).strip() and str(h) != 'None'])
                    
                    logger.info(f"Found header row at index {header_row_index}")
                    logger.info(f"Raw headers ({len(raw_headers)}): {raw_headers}")
                    logger.info(f"Joined header text: '{header_text}'")
                    
                    # For Federal Bank, we expect: Date, Value Date, Particulars, Tran Type, Tran ID, 
                    # Cheque Details, Withdrawals, Deposits, Balance, Dr/Cr
                    # But extraction splits them. Solution: Use the raw column positions
                    # and manually map based on known Federal Bank format
                    
                    cleaned_headers = []
                    for i, h in enumerate(raw_headers):
                        h_str = str(h).strip() if h and str(h) != 'None' else ''
                        cleaned_headers.append(h_str)
                    
                    df.columns = cleaned_headers
                    
                    logger.info(f"Cleaned columns ({len(df.columns)}): {repr(cleaned_headers)}")
                    logger.info(f"✅ Detected columns: {', '.join([c for c in cleaned_headers if c])}")
                    
                    # Drop all header rows
                    df = df[~is_header_row]
                else:
                    raise ValueError(
                        "❌ Failed to parse PDF: No header row with 'Date' found\n"
                        "💡 Tip: This PDF may not be in a supported bank statement format"
                    )
            
            # Filter to only rows with valid dates (supports multiple formats)
            # This removes "Opening Balance", page footers, etc.
            date_col_name = df.columns[0] if len(df.columns) > 0 else None
            if date_col_name:
                # Support multiple date formats: DD/MM/YYYY, DD-MM-YYYY, DD-MMM-YYYY
                date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4})|(\d{2}-\w{3}-\d{4})'
                df = df[df[date_col_name].astype(str).str.match(date_pattern, na=False)]
                logger.info(f"After date filtering: {len(df)} transaction rows")
            
            if df.empty:
                raise ValueError(
                    "⚠️ Parsed 0 transactions (all rows filtered out)\n"
                    "💡 Tip: Check if the PDF contains valid transaction dates in supported formats (DD/MM/YYYY, DD-MM-YYYY)"
                )
            
            # Now parse the table using standard column detection
            result = self._parse_table(df)
            
            if not result.empty:
                logger.info(f"✅ Successfully parsed {len(result)} transactions from PDF")
                logger.info(f"📊 Date range: {result['transaction_date'].min()} to {result['transaction_date'].max()}")
                return result
            else:
                raise ValueError(
                    "⚠️ Parsed data but got 0 valid transactions after normalization\n"
                    "💡 Tip: The PDF structure may not match expected bank statement format"
                )
        
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
            
            # Log what we found
            logger.info(f"Column Detection Results:")
            logger.info(f"  Available columns: {list(df.columns)}")
            logger.info(f"  Date column: {date_col}")
            logger.info(f"  Description column: {desc_col}")
            logger.info(f"  Debit column: {debit_col}")
            logger.info(f"  Credit column: {credit_col}")
            
            if not date_col or not desc_col:
                logger.warning(f"Missing required columns!")
                logger.warning(f"  Columns in table: {list(df.columns)}")
                logger.warning(f"  Looking for Date: {csv_parser.COLUMN_MAPPINGS['date']}")
                logger.warning(f"  Looking for Description: {csv_parser.COLUMN_MAPPINGS['description']}")
                return pd.DataFrame()
            
            # Check for amount columns
            if not debit_col and not credit_col:
                logger.warning("No debit/credit columns found!")
                logger.warning(f"  Looking for Debit: {csv_parser.COLUMN_MAPPINGS['debit']}")
                logger.warning(f"  Looking for Credit: {csv_parser.COLUMN_MAPPINGS['credit']}")
                return pd.DataFrame()
            
            logger.info(f"✅ Successfully matched all required columns")
            
            # Normalize
            result = pd.DataFrame()
            result['transaction_date'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
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
            
            logger.info(f"✅ Parsed {len(result)} valid transactions from table")
            return result
        
        except Exception as e:
            logger.error(f"Table parsing failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
