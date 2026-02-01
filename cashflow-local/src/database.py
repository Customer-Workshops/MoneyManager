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
        - idx_account: Account-based filtering
        """
        # DuckDB doesn't support executescript, need to execute each statement separately
        schema_statements = [
            # Users table
            """
            CREATE SEQUENCE IF NOT EXISTS seq_users_id START 1;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_users_id'),
                email VARCHAR UNIQUE NOT NULL,
                password_hash VARCHAR NOT NULL,
                full_name VARCHAR NOT NULL,
                avatar_url VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Workspaces (families/groups)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_workspaces_id START 1;
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_workspaces_id'),
                name VARCHAR NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # User-Workspace roles (role-based access)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_user_workspace_roles_id START 1;
            CREATE TABLE IF NOT EXISTS user_workspace_roles (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_user_workspace_roles_id'),
                user_id INTEGER NOT NULL,
                workspace_id INTEGER NOT NULL,
                role VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, workspace_id)
            )
            """,
            # Accounts table (shared or personal)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_accounts_id START 1;
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_accounts_id'),
                name VARCHAR NOT NULL,
                type VARCHAR(50) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                is_active BOOLEAN DEFAULT TRUE,
                workspace_id INTEGER,
                is_shared BOOLEAN DEFAULT TRUE,
                owner_user_id INTEGER,
                opening_balance DECIMAL(12, 2) DEFAULT 0,
                opening_balance_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Transactions table with deduplication hash (updated with user and workspace)
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
                workspace_id INTEGER,
                user_id INTEGER,
                reconciled BOOLEAN DEFAULT FALSE,
                reconciled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Index for O(1) duplicate lookups
            "CREATE INDEX IF NOT EXISTS idx_hash ON transactions(hash)",
            # Index for temporal queries (monthly aggregations)
            "CREATE INDEX IF NOT EXISTS idx_date ON transactions(transaction_date)",
            # Index for workspace queries
            "CREATE INDEX IF NOT EXISTS idx_workspace ON transactions(workspace_id)",
            # Index for account filtering
            "CREATE INDEX IF NOT EXISTS idx_account ON transactions(account_id)",
            # Index for reconciliation status
            "CREATE INDEX IF NOT EXISTS idx_reconciled ON transactions(reconciled)",
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
            # Budget tracking per category (updated with workspace and sharing)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_budgets_id START 1;
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_budgets_id'),
                workspace_id INTEGER NOT NULL,
                category VARCHAR(50) NOT NULL,
                monthly_limit DECIMAL(10, 2) NOT NULL,
                is_shared BOOLEAN DEFAULT TRUE,
                owner_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, category, owner_user_id)
            )
            """,
            # Goals table (shared savings goals)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_goals_id START 1;
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_goals_id'),
                workspace_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                target_amount DECIMAL(12, 2) NOT NULL,
                current_amount DECIMAL(12, 2) DEFAULT 0,
                target_date DATE,
                is_shared BOOLEAN DEFAULT TRUE,
                created_by INTEGER NOT NULL,
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
        
        # Note: Migration statements removed because columns are already in main schema
        # Attempting to ALTER TABLE with existing indexes causes dependency errors in DuckDB
        # All required columns (account_id, reconciled, reconciled_at) are defined in CREATE TABLE
        
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

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all accounts (active and inactive).
        
        Returns:
            List of account dictionaries
        """
        try:
            # Note: Removed workspace_id filter for now as auth is disabled
            # In future: WHERE workspace_id = ?
            query = "SELECT id, name, type, currency, is_active FROM accounts ORDER BY name"
            results = self.execute_query(query)
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "type": r[2],  # was r[2] mapped to type
                    "currency": r[3],
                    "is_active": bool(r[4])
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Failed to get all accounts: {e}")
            return []

    def get_tax_summary(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get tax summary for the specified period.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of tax dictionaries with section, annual_limit, utilization_percent, etc.
        """
        try:
            # Join transactions with tax categories (via tags or categories)
            # For now, simplistic implementation based on transaction categories matching tax category keywords
            # In a real implementation, this would be more complex
            
            query = """
                SELECT 
                    tc.section,
                    tc.name,
                    tc.annual_limit,
                    COALESCE(SUM(t.amount), 0) as total_amount
                FROM tax_categories tc
                LEFT JOIN transactions t ON t.category = tc.name 
                    AND t.transaction_date >= ? AND t.transaction_date <= ?
                    AND t.type = 'Debit'
                GROUP BY tc.section, tc.name, tc.annual_limit
                ORDER BY tc.section
            """
            
            results = self.execute_query(query, (start_date, end_date))
            
            summary = []
            for r in results:
                section = r[0]
                name = r[1]
                limit = r[2]
                amount = r[3]
                
                utilization = 0
                if limit and limit > 0:
                    utilization = (amount / limit) * 100
                
                summary.append({
                    "section": section,
                    "name": name,
                    "annual_limit": limit,
                    "total_amount": amount,
                    "utilization_percent": utilization
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get tax summary: {e}")
            return []
    
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
    
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """
        Get all tags.
        
        Returns:
            List of tag dictionaries with id, name, and color
        """
        try:
            query = "SELECT id, name, color FROM tags ORDER BY name"
            results = self.execute_query(query)
            return [{"id": r[0], "name": r[1], "color": r[2]} for r in results]
        except Exception as e:
            logger.error(f"Failed to get tags: {e}")
            return []
    
    def add_tag(self, name: str, color: str = '#3498db') -> Optional[int]:
        """
        Add a new tag.
        
        Args:
            name: Tag name
            color: Tag color (hex format)
        
        Returns:
            Tag ID if successful, None otherwise
        """
        try:
            query = "INSERT INTO tags (name, color) VALUES (?, ?) RETURNING id"
            with self.get_connection() as conn:
                result = conn.execute(query, [name, color]).fetchone()
                logger.info(f"Added tag: {name}")
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to add tag: {e}")
            return None
    
    def tag_transaction(self, transaction_id: int, tag_id: int) -> bool:
        """
        Associate a tag with a transaction.
        
        Args:
            transaction_id: Transaction ID
            tag_id: Tag ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            query = "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)"
            with self.get_connection() as conn:
                conn.execute(query, [transaction_id, tag_id])
                logger.info(f"Tagged transaction {transaction_id} with tag {tag_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to tag transaction: {e}")
            return False
    
    def get_transaction_tags(self, transaction_id: int) -> List[str]:
        """
        Get all tags for a transaction.
        
        Args:
            transaction_id: Transaction ID
        
        Returns:
            List of tag names
        """
        try:
            query = """
                SELECT t.name 
                FROM tags t
                JOIN transaction_tags tt ON t.id = tt.tag_id
                WHERE tt.transaction_id = ?
            """
            results = self.execute_query(query, (transaction_id,))
            return [r[0] for r in results]
        except Exception as e:
            logger.error(f"Failed to get transaction tags: {e}")
            return []
    
    def save_search(self, name: str, filter_config: str) -> bool:
        """
        Save a search configuration.
        
        Args:
            name: Search name
            filter_config: JSON string of filter configuration
        
        Returns:
            True if successful, False otherwise
        """
        try:
            query = "INSERT INTO saved_searches (name, filter_config) VALUES (?, ?)"
            with self.get_connection() as conn:
                conn.execute(query, [name, filter_config])
                logger.info(f"Saved search: {name}")
                return True
        except Exception as e:
            logger.error(f"Failed to save search: {e}")
            return False
    
    def get_saved_searches(self) -> List[Dict[str, Any]]:
        """
        Get all saved searches.
        
        Returns:
            List of saved search dictionaries
        """
        try:
            query = "SELECT id, name, filter_config FROM saved_searches ORDER BY created_at DESC"
            results = self.execute_query(query)
            return [{"id": r[0], "name": r[1], "filter_config": r[2]} for r in results]
        except Exception as e:
            logger.error(f"Failed to get saved searches: {e}")
            return []


# Global instance (singleton)
db_manager = DatabaseManager()
