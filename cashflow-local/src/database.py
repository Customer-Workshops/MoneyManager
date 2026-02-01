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
        4. accounts: Bank account information with opening balances
        5. account_balances: Historical balance tracking per account
        
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
            # Accounts table for tracking bank accounts
            """
            CREATE SEQUENCE IF NOT EXISTS seq_accounts_id START 1;
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_accounts_id'),
                name VARCHAR(100) UNIQUE NOT NULL,
                account_number VARCHAR(50),
                account_type VARCHAR(20) DEFAULT 'Checking',
                opening_balance DECIMAL(12, 2) DEFAULT 0.00,
                opening_balance_date DATE,
                currency VARCHAR(3) DEFAULT 'INR',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Account balances history table
            """
            CREATE SEQUENCE IF NOT EXISTS seq_account_balances_id START 1;
            CREATE TABLE IF NOT EXISTS account_balances (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_account_balances_id'),
                account_id INTEGER NOT NULL,
                balance_date DATE NOT NULL,
                calculated_balance DECIMAL(12, 2) NOT NULL,
                actual_balance DECIMAL(12, 2),
                variance DECIMAL(12, 2),
                is_reconciled BOOLEAN DEFAULT FALSE,
                reconciled_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(account_id, balance_date)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_account_balances_date ON account_balances(balance_date)",
            "CREATE INDEX IF NOT EXISTS idx_account_balances_account ON account_balances(account_id)"
        ]
        
        # Migration: Add reconciliation fields to transactions table if they don't exist
        migration_statements = [
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INTEGER",
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS reconciled BOOLEAN DEFAULT FALSE",
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMP",
            "CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_reconciled ON transactions(reconciled)"
        ]
        
        try:
            # Execute each statement individually
            for statement in schema_statements:
                self._connection.execute(statement)
            
            # Execute migration statements
            for statement in migration_statements:
                self._connection.execute(statement)
            
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise
    
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
        account_id: Optional[int] = None,
        reconciled: Optional[bool] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve transactions with optional filtering.
        
        Args:
            start_date: Filter transactions after this date
            end_date: Filter transactions before this date
            category: Filter by category
            account_id: Filter by account
            reconciled: Filter by reconciliation status
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
        
        if account_id is not None:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if reconciled is not None:
            query += " AND reconciled = ?"
            params.append(reconciled)
        
        query += f" ORDER BY transaction_date DESC LIMIT {limit}"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, params).fetchdf()  # Return as pandas DataFrame
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve transactions: {e}")
            raise
    
    def get_accounts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve all accounts.
        
        Args:
            active_only: If True, only return active accounts
        
        Returns:
            List of account dictionaries
        """
        query = "SELECT * FROM accounts"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve accounts: {e}")
            raise
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific account by ID.
        
        Args:
            account_id: Account ID
        
        Returns:
            Account dictionary or None if not found
        """
        query = "SELECT * FROM accounts WHERE id = ?"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, [account_id]).fetchdf()
                if len(results) > 0:
                    return results.to_dict('records')[0]
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve account: {e}")
            raise
    
    def calculate_account_balance(
        self,
        account_id: int,
        as_of_date: Optional[datetime] = None
    ) -> float:
        """
        Calculate account balance as of a specific date.
        
        Args:
            account_id: Account ID
            as_of_date: Calculate balance as of this date (defaults to today)
        
        Returns:
            Calculated balance
        """
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        opening_balance = account.get('opening_balance', 0) or 0
        opening_date = account.get('opening_balance_date')
        
        query = """
            SELECT SUM(
                CASE 
                    WHEN type = 'Credit' THEN amount 
                    WHEN type = 'Debit' THEN -amount 
                    ELSE 0 
                END
            ) as net_change
            FROM transactions
            WHERE account_id = ?
        """
        params = [account_id]
        
        if opening_date:
            query += " AND transaction_date >= ?"
            params.append(opening_date)
        
        if as_of_date:
            query += " AND transaction_date <= ?"
            params.append(as_of_date)
        
        try:
            with self.get_connection() as conn:
                result = conn.execute(query, params).fetchone()
                net_change = result[0] if result[0] is not None else 0
                return float(opening_balance) + float(net_change)
        except Exception as e:
            logger.error(f"Failed to calculate account balance: {e}")
            raise
    
    def mark_transactions_reconciled(
        self,
        transaction_ids: List[int],
        reconciled: bool = True
    ) -> int:
        """
        Mark transactions as reconciled or unreconciled.
        
        Args:
            transaction_ids: List of transaction IDs to update
            reconciled: True to mark as reconciled, False to unmark
        
        Returns:
            Number of transactions updated
        """
        if not transaction_ids:
            return 0
        
        try:
            placeholders = ", ".join(["?" for _ in transaction_ids])
            query = f"""
                UPDATE transactions 
                SET reconciled = ?, 
                    reconciled_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE id IN ({placeholders})
            """
            
            with self.get_connection() as conn:
                conn.execute(query, [reconciled, reconciled] + transaction_ids)
                logger.info(f"Marked {len(transaction_ids)} transactions as {'reconciled' if reconciled else 'unreconciled'}")
                return len(transaction_ids)
        except Exception as e:
            logger.error(f"Failed to mark transactions as reconciled: {e}")
            raise
    
    def save_balance_snapshot(
        self,
        account_id: int,
        balance_date: datetime,
        calculated_balance: float,
        actual_balance: Optional[float] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Save a balance snapshot for reconciliation.
        
        Args:
            account_id: Account ID
            balance_date: Date of the balance snapshot
            calculated_balance: App-calculated balance
            actual_balance: User-entered actual bank balance
            notes: Optional notes about the reconciliation
        """
        variance = None
        is_reconciled = False
        
        if actual_balance is not None:
            variance = actual_balance - calculated_balance
            is_reconciled = abs(variance) < 0.01  # Consider reconciled if difference < 1 cent
        
        try:
            with self.get_connection() as conn:
                # Try to insert or update
                conn.execute("""
                    INSERT INTO account_balances 
                    (account_id, balance_date, calculated_balance, actual_balance, variance, is_reconciled, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (account_id, balance_date) DO UPDATE SET
                        calculated_balance = EXCLUDED.calculated_balance,
                        actual_balance = EXCLUDED.actual_balance,
                        variance = EXCLUDED.variance,
                        is_reconciled = EXCLUDED.is_reconciled,
                        notes = EXCLUDED.notes,
                        reconciled_at = CASE WHEN EXCLUDED.is_reconciled THEN CURRENT_TIMESTAMP ELSE NULL END
                """, [account_id, balance_date, calculated_balance, actual_balance, variance, is_reconciled, notes])
                logger.info(f"Saved balance snapshot for account {account_id} on {balance_date}")
        except Exception as e:
            logger.error(f"Failed to save balance snapshot: {e}")
            raise
    
    def get_balance_history(
        self,
        account_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get balance history for an account.
        
        Args:
            account_id: Account ID
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            List of balance history records
        """
        query = "SELECT * FROM account_balances WHERE account_id = ?"
        params = [account_id]
        
        if start_date:
            query += " AND balance_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND balance_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY balance_date DESC"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, params).fetchdf()
                return results.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to retrieve balance history: {e}")
            raise
    
    def close(self) -> None:
        """Close database connection. Called on application shutdown."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")


# Global instance (singleton)
db_manager = DatabaseManager()
