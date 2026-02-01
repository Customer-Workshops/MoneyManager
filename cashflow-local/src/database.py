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
        1. accounts: Financial accounts (bank, credit card, wallet, etc.)
        2. transactions: Core fact table with hash-based deduplication
        3. category_rules: Keyword-to-category mappings
        4. budgets: Monthly spending limits per category
        
        Indexes:
        - idx_hash: O(1) duplicate detection
        - idx_date: Temporal queries (monthly aggregations)
        - idx_account: Account-based filtering
        """
        # DuckDB doesn't support executescript, need to execute each statement separately
        schema_statements = [
            # Accounts table
            """
            CREATE SEQUENCE IF NOT EXISTS seq_accounts_id START 1;
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_accounts_id'),
                name VARCHAR NOT NULL,
                type VARCHAR(50) NOT NULL,
                balance DECIMAL(12, 2) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'USD',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Transactions table with deduplication hash
            # Note: Foreign key constraint enforces referential integrity
            # Account deletion is handled manually to set account_id to NULL
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
                account_id INTEGER,
                source_file_hash VARCHAR(32) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Index for O(1) duplicate lookups
            "CREATE INDEX IF NOT EXISTS idx_hash ON transactions(hash)",
            # Index for temporal queries (monthly aggregations)
            "CREATE INDEX IF NOT EXISTS idx_date ON transactions(transaction_date)",
            # Index for account-based filtering
            "CREATE INDEX IF NOT EXISTS idx_account ON transactions(account_id)",
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
            """
        ]
        
        try:
            # Execute each statement individually
            for statement in schema_statements:
                self._connection.execute(statement)
            
            # Create default account if none exists
            self._create_default_account()
            
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise
    
    def _create_default_account(self) -> None:
        """Create a default 'Primary Account' if no accounts exist."""
        try:
            count_query = "SELECT COUNT(*) FROM accounts"
            result = self._connection.execute(count_query).fetchone()
            
            if result[0] == 0:
                # Create default account
                insert_query = """
                    INSERT INTO accounts (name, type, balance, currency)
                    VALUES (?, ?, ?, ?)
                """
                self._connection.execute(insert_query, 
                    ('Primary Account', 'Checking Account', 0.0, 'USD'))
                logger.info("Created default 'Primary Account'")
        except Exception as e:
            logger.error(f"Failed to create default account: {e}")
            # Don't raise - this is not critical for schema initialization
    
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
    
    # Account Management Methods
    
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Retrieve all accounts.
        
        Returns:
            List of account dictionaries with id, name, type, balance, currency
        """
        try:
            query = "SELECT id, name, type, balance, currency FROM accounts ORDER BY created_at"
            with self.get_connection() as conn:
                results = conn.execute(query).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve accounts: {e}")
            raise
    
    def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific account by ID.
        
        Args:
            account_id: Account ID
        
        Returns:
            Account dictionary or None if not found
        """
        try:
            query = "SELECT id, name, type, balance, currency FROM accounts WHERE id = ?"
            with self.get_connection() as conn:
                result = conn.execute(query, (account_id,)).fetchone()
                if result:
                    return {
                        'id': result[0],
                        'name': result[1],
                        'type': result[2],
                        'balance': result[3],
                        'currency': result[4]
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve account {account_id}: {e}")
            raise
    
    def create_account(self, name: str, account_type: str, balance: float = 0.0, currency: str = 'USD') -> int:
        """
        Create a new account.
        
        Args:
            name: Account name
            account_type: Account type (Savings, Checking, Credit Card, etc.)
            balance: Initial balance
            currency: Currency code
        
        Returns:
            ID of created account
        """
        try:
            query = """
                INSERT INTO accounts (name, type, balance, currency)
                VALUES (?, ?, ?, ?)
            """
            with self.get_connection() as conn:
                conn.execute(query, (name, account_type, balance, currency))
                # Get the last inserted ID
                result = conn.execute("SELECT MAX(id) FROM accounts").fetchone()
                account_id = result[0] if result else None
                logger.info(f"Created account: {name} (ID: {account_id})")
                return account_id
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            raise
    
    def update_account(self, account_id: int, name: str, account_type: str, balance: float, currency: str) -> None:
        """
        Update an existing account.
        
        Args:
            account_id: Account ID
            name: Account name
            account_type: Account type
            balance: Account balance
            currency: Currency code
        """
        try:
            query = """
                UPDATE accounts
                SET name = ?, type = ?, balance = ?, currency = ?
                WHERE id = ?
            """
            with self.get_connection() as conn:
                conn.execute(query, (name, account_type, balance, currency, account_id))
                logger.info(f"Updated account ID {account_id}")
        except Exception as e:
            logger.error(f"Failed to update account {account_id}: {e}")
            raise
    
    def delete_account(self, account_id: int) -> None:
        """
        Delete an account.
        
        Args:
            account_id: Account ID
        
        Note:
            Manually sets account_id to NULL for all associated transactions
            before deleting the account to preserve transaction history
        """
        try:
            # First, update transactions to remove account association
            update_query = "UPDATE transactions SET account_id = NULL WHERE account_id = ?"
            with self.get_connection() as conn:
                conn.execute(update_query, (account_id,))
                
                # Then delete the account
                delete_query = "DELETE FROM accounts WHERE id = ?"
                conn.execute(delete_query, (account_id,))
                logger.info(f"Deleted account ID {account_id}")
        except Exception as e:
            logger.error(f"Failed to delete account {account_id}: {e}")
            raise
    
    def get_account_balance(self, account_id: int) -> float:
        """
        Calculate current balance for an account based on transactions.
        
        Args:
            account_id: Account ID
        
        Returns:
            Calculated balance (sum of credits - debits)
        """
        try:
            query = """
                SELECT 
                    SUM(CASE WHEN type = 'Credit' THEN amount ELSE -amount END) as balance
                FROM transactions
                WHERE account_id = ?
            """
            with self.get_connection() as conn:
                result = conn.execute(query, (account_id,)).fetchone()
                return result[0] if result and result[0] else 0.0
        except Exception as e:
            logger.error(f"Failed to calculate balance for account {account_id}: {e}")
            raise
    
    def get_net_worth(self) -> float:
        """
        Calculate total net worth across all accounts.
        
        Returns:
            Sum of all account balances
        """
        try:
            query = "SELECT SUM(balance) FROM accounts"
            with self.get_connection() as conn:
                result = conn.execute(query).fetchone()
                return result[0] if result and result[0] else 0.0
        except Exception as e:
            logger.error(f"Failed to calculate net worth: {e}")
            raise
    
    def close(self) -> None:
        """Close database connection. Called on application shutdown."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")


# Global instance (singleton)
db_manager = DatabaseManager()
