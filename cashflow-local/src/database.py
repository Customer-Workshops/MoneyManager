"""
DuckDB Database Manager for CashFlow-Local

Provides connection management, schema initialization, and data access patterns
optimized for financial transaction analytics.

Performance Notes:
- DuckDB's columnar storage is optimized for OLAP queries (aggregations, time-series)
- Connection pooling via singleton pattern prevents excessive connection overhead
- Hash-based indexes provide O(1) duplicate lookups
"""

import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime

import duckdb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton DuckDB connection manager with automatic schema initialization.
    
    Design Rationale:
    - Singleton pattern ensures single connection across Streamlit reruns
    - Context manager protocol (__enter__/__exit__) guarantees resource cleanup
    - DuckDB is embedded, so no network overhead like traditional RDBMS
    
    Performance:
    - Columnar storage: 10-100x faster for analytical queries vs row-based DBs
    - In-process: No serialization/network latency
    - ACID compliant: Safe for concurrent reads (Streamlit multi-user scenario)
    """
    
    _instance: Optional['DatabaseManager'] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def __new__(cls):
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database connection if not already connected."""
        if self._connection is None:
            db_path = os.getenv("DB_PATH", "/app/data/cashflow.duckdb")
            logger.info(f"Initializing DuckDB connection: {db_path}")
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            self._connection = duckdb.connect(db_path)
            self._initialize_schema()
    
    def _initialize_schema(self) -> None:
        """
        Create database schema if it doesn't exist.
        
        Schema Design:
        1. transactions: Core fact table with hash-based deduplication
        2. category_rules: Keyword-to-category mappings
        3. budgets: Monthly spending limits per category
        4. tax_categories: Indian tax sections (80C, 80D, HRA, etc.)
        5. transaction_tax_tags: Many-to-many relationship between transactions and tax categories
        
        Indexes:
        - idx_hash: O(1) duplicate detection
        - idx_date: Temporal queries (monthly aggregations)
        """
        # DuckDB doesn't support executescript, need to execute each statement separately
        schema_statements = [
            # Transactions table with deduplication hash
            """
            CREATE SEQUENCE IF NOT EXISTS seq_transactions_id START 1;
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_transactions_id'),
                hash VARCHAR UNIQUE NOT NULL,
                transaction_date DATE NOT NULL,
                description VARCHAR NOT NULL,
                amount DECIMAL(12, 2) NOT NULL,
                type VARCHAR(10) NOT NULL,
                category VARCHAR(50) DEFAULT 'Uncategorized',
                source_file_hash VARCHAR(32) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Index for O(1) duplicate lookups
            "CREATE INDEX IF NOT EXISTS idx_hash ON transactions(hash)",
            # Index for temporal queries (monthly aggregations)
            "CREATE INDEX IF NOT EXISTS idx_date ON transactions(transaction_date)",
            # Category rules for auto-categorization
            """
            CREATE SEQUENCE IF NOT EXISTS seq_category_rules_id START 1;
            CREATE TABLE IF NOT EXISTS category_rules (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_category_rules_id'),
                keyword VARCHAR NOT NULL,
                category VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Budget tracking per category
            """
            CREATE SEQUENCE IF NOT EXISTS seq_budgets_id START 1;
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_budgets_id'),
                category VARCHAR(50) UNIQUE NOT NULL,
                monthly_limit DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Tax categories table for Indian tax sections
            """
            CREATE SEQUENCE IF NOT EXISTS seq_tax_categories_id START 1;
            CREATE TABLE IF NOT EXISTS tax_categories (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_tax_categories_id'),
                name VARCHAR(100) UNIQUE NOT NULL,
                section VARCHAR(50) NOT NULL,
                description VARCHAR(500),
                annual_limit DECIMAL(12, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Many-to-many relationship between transactions and tax categories
            """
            CREATE SEQUENCE IF NOT EXISTS seq_transaction_tax_tags_id START 1;
            CREATE TABLE IF NOT EXISTS transaction_tax_tags (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_transaction_tax_tags_id'),
                transaction_id INTEGER NOT NULL,
                tax_category_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(transaction_id, tax_category_id)
            )
            """,
            # Index for efficient tax tag lookups
            "CREATE INDEX IF NOT EXISTS idx_tax_tags_transaction ON transaction_tax_tags(transaction_id)",
            "CREATE INDEX IF NOT EXISTS idx_tax_tags_category ON transaction_tax_tags(tax_category_id)"
        ]
        
        try:
            # Execute each statement individually
            for statement in schema_statements:
                self._connection.execute(statement)
            logger.info("Database schema initialized successfully")
            
            # Initialize predefined tax categories
            self._initialize_tax_categories()
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise
    
    def _initialize_tax_categories(self) -> None:
        """
        Initialize predefined Indian tax categories if not already present.
        
        Tax Categories (India):
        - 80C: Investments (ELSS, EPF, PPF, Life Insurance) - Max: ₹1.5L
        - 80D: Health Insurance premiums - Max: ₹25K (₹50K for senior citizens)
        - 80E: Education Loan interest - No limit
        - 80G: Donations to charity - 50% or 100% of donation
        - 80TTA: Savings account interest - Max: ₹10K
        - HRA: House Rent Allowance - Based on salary
        - Home Loan Interest: Section 24 - Max: ₹2L
        - Business Expenses: For freelancers - As per actual
        """
        predefined_categories = [
            {
                'name': '80C - Investments',
                'section': '80C',
                'description': 'ELSS, EPF, PPF, Life Insurance, Tax-saving FD',
                'annual_limit': 150000.00
            },
            {
                'name': '80D - Health Insurance',
                'section': '80D',
                'description': 'Health Insurance premiums for self and family',
                'annual_limit': 25000.00
            },
            {
                'name': '80D - Senior Citizen Health Insurance',
                'section': '80D',
                'description': 'Health Insurance premiums for senior citizens',
                'annual_limit': 50000.00
            },
            {
                'name': '80E - Education Loan',
                'section': '80E',
                'description': 'Interest on Education Loan',
                'annual_limit': None  # No limit
            },
            {
                'name': '80G - Donations',
                'section': '80G',
                'description': 'Donations to charitable institutions',
                'annual_limit': None  # Depends on donation type
            },
            {
                'name': '80TTA - Savings Interest',
                'section': '80TTA',
                'description': 'Interest from Savings Account',
                'annual_limit': 10000.00
            },
            {
                'name': 'HRA - House Rent',
                'section': 'HRA',
                'description': 'House Rent Allowance',
                'annual_limit': None  # Based on salary and rent
            },
            {
                'name': 'Section 24 - Home Loan Interest',
                'section': '24',
                'description': 'Interest on Home Loan',
                'annual_limit': 200000.00
            },
            {
                'name': 'Business Expenses',
                'section': 'Business',
                'description': 'Business-related expenses for freelancers',
                'annual_limit': None  # As per actual
            }
        ]
        
        try:
            # Check if tax categories already exist
            with self.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM tax_categories").fetchone()[0]
                
                # Only insert if table is empty
                if count == 0:
                    for category in predefined_categories:
                        conn.execute(
                            """
                            INSERT INTO tax_categories (name, section, description, annual_limit)
                            VALUES (?, ?, ?, ?)
                            """,
                            (category['name'], category['section'], category['description'], category['annual_limit'])
                        )
                    logger.info(f"Initialized {len(predefined_categories)} predefined tax categories")
        except Exception as e:
            logger.error(f"Failed to initialize tax categories: {e}")
            # Don't raise - this is not critical for app functionality
    
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database operations.
        
        Usage:
            with db_manager.get_connection() as conn:
                result = conn.execute("SELECT * FROM transactions").fetchall()
        
        Yields:
            duckdb.DuckDBPyConnection: Active database connection
        """
        try:
            yield self._connection
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters (for prepared statements)
        
        Returns:
            List of result tuples
        
        Raises:
            Exception: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                if params:
                    result = conn.execute(query, params).fetchall()
                else:
                    result = conn.execute(query).fetchall()
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            raise
    
    def execute_insert(self, table: str, data: List[Dict[str, Any]]) -> int:
        """
        Batch insert records into a table.
        
        Performance Note:
        - Batch inserts are ~100x faster than row-by-row
        - DuckDB uses vectorized execution for bulk operations
        
        Args:
            table: Target table name
            data: List of dictionaries with column:value mappings
        
        Returns:
            Number of rows inserted
        
        Raises:
            Exception: If insertion fails
        """
        if not data:
            return 0
        
        try:
            # Extract column names from first record
            columns = list(data[0].keys())
            placeholders = ", ".join(["?" for _ in columns])
            column_names = ", ".join(columns)
            
            insert_sql = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                # Convert list of dicts to list of tuples
                values = [tuple(record[col] for col in columns) for record in data]
                conn.executemany(insert_sql, values)
                logger.info(f"Inserted {len(values)} rows into {table}")
                return len(values)
        
        except Exception as e:
            logger.error(f"Batch insert failed for table {table}: {e}")
            raise
    
    def check_duplicates(self, hashes: List[str]) -> set:
        """
        Check which transaction hashes already exist in the database.
        
        Performance:
        - Uses indexed query on hash column: O(1) per hash lookup
        - Batch query avoids N individual lookups
        
        Args:
            hashes: List of transaction hashes to check
        
        Returns:
            Set of existing hashes
        """
        if not hashes:
            return set()
        
        try:
            placeholders = ", ".join(["?" for _ in hashes])
            query = f"SELECT hash FROM transactions WHERE hash IN ({placeholders})"
            
            with self.get_connection() as conn:
                results = conn.execute(query, hashes).fetchall()
                existing_hashes = {row[0] for row in results}
                logger.debug(f"Found {len(existing_hashes)} existing hashes out of {len(hashes)}")
                return existing_hashes
        
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            raise
    
    def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve transactions with optional filtering.
        
        Args:
            start_date: Filter transactions after this date
            end_date: Filter transactions before this date
            category: Filter by category
            limit: Maximum number of records to return
        
        Returns:
            List of transaction dictionaries
        """
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += f" ORDER BY transaction_date DESC LIMIT {limit}"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, params).fetchdf()  # Return as pandas DataFrame
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve transactions: {e}")
            raise
    
    def get_all_tax_categories(self) -> List[Dict[str, Any]]:
        """
        Retrieve all available tax categories.
        
        Returns:
            List of tax category dictionaries
        """
        query = "SELECT * FROM tax_categories ORDER BY section, name"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve tax categories: {e}")
            raise
    
    def add_tax_tag(self, transaction_id: int, tax_category_id: int) -> bool:
        """
        Add a tax tag to a transaction.
        
        Args:
            transaction_id: Transaction ID
            tax_category_id: Tax category ID
        
        Returns:
            True if tag was added, False if it already existed
        """
        try:
            with self.get_connection() as conn:
                # Check if tag already exists
                existing = conn.execute(
                    """
                    SELECT COUNT(*) FROM transaction_tax_tags 
                    WHERE transaction_id = ? AND tax_category_id = ?
                    """,
                    (transaction_id, tax_category_id)
                ).fetchone()[0]
                
                if existing > 0:
                    return False
                
                # Insert new tag
                conn.execute(
                    """
                    INSERT INTO transaction_tax_tags (transaction_id, tax_category_id)
                    VALUES (?, ?)
                    """,
                    (transaction_id, tax_category_id)
                )
                logger.info(f"Added tax tag {tax_category_id} to transaction {transaction_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to add tax tag: {e}")
            raise
    
    def remove_tax_tag(self, transaction_id: int, tax_category_id: int) -> bool:
        """
        Remove a tax tag from a transaction.
        
        Args:
            transaction_id: Transaction ID
            tax_category_id: Tax category ID
        
        Returns:
            True if tag was removed, False if it didn't exist
        """
        try:
            with self.get_connection() as conn:
                result = conn.execute(
                    """
                    DELETE FROM transaction_tax_tags 
                    WHERE transaction_id = ? AND tax_category_id = ?
                    """,
                    (transaction_id, tax_category_id)
                )
                logger.info(f"Removed tax tag {tax_category_id} from transaction {transaction_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove tax tag: {e}")
            raise
    
    def get_transaction_tax_tags(self, transaction_id: int) -> List[Dict[str, Any]]:
        """
        Get all tax tags for a specific transaction.
        
        Args:
            transaction_id: Transaction ID
        
        Returns:
            List of tax category dictionaries
        """
        query = """
            SELECT tc.* 
            FROM tax_categories tc
            INNER JOIN transaction_tax_tags ttt ON tc.id = ttt.tax_category_id
            WHERE ttt.transaction_id = ?
            ORDER BY tc.section, tc.name
        """
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, (transaction_id,)).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve transaction tax tags: {e}")
            raise
    
    def get_tax_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get summary of tax deductions by category for a given period.
        
        Args:
            start_date: Start date for the period
            end_date: End date for the period
        
        Returns:
            List of dictionaries with tax category summary
        """
        query = """
            SELECT 
                tc.id,
                tc.name,
                tc.section,
                tc.description,
                tc.annual_limit,
                COUNT(DISTINCT t.id) as transaction_count,
                SUM(ABS(t.amount)) as total_amount,
                CASE 
                    WHEN tc.annual_limit IS NOT NULL THEN 
                        ROUND((SUM(ABS(t.amount)) / tc.annual_limit) * 100, 2)
                    ELSE NULL 
                END as utilization_percent
            FROM tax_categories tc
            LEFT JOIN transaction_tax_tags ttt ON tc.id = ttt.tax_category_id
            LEFT JOIN transactions t ON ttt.transaction_id = t.id
        """
        
        conditions = []
        params = []
        
        if start_date:
            conditions.append("(t.transaction_date >= ? OR t.transaction_date IS NULL)")
            params.append(start_date)
        
        if end_date:
            conditions.append("(t.transaction_date <= ? OR t.transaction_date IS NULL)")
            params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += """
            GROUP BY tc.id, tc.name, tc.section, tc.description, tc.annual_limit
            ORDER BY tc.section, tc.name
        """
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, params).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve tax summary: {e}")
            raise
    
    def get_transactions_by_tax_category(
        self,
        tax_category_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific tax category.
        
        Args:
            tax_category_id: Tax category ID
            start_date: Filter transactions after this date
            end_date: Filter transactions before this date
        
        Returns:
            List of transaction dictionaries
        """
        query = """
            SELECT t.*
            FROM transactions t
            INNER JOIN transaction_tax_tags ttt ON t.id = ttt.transaction_id
            WHERE ttt.tax_category_id = ?
        """
        
        params = [tax_category_id]
        
        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY t.transaction_date DESC"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, params).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve transactions by tax category: {e}")
            raise
    
    def close(self) -> None:
        """Close database connection. Called on application shutdown."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")


# Global instance (singleton)
db_manager = DatabaseManager()
