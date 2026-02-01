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
from datetime import datetime, date

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
        1. categories: Normalized category management (Type, Icon, Color)
        2. transactions: Core fact table with category_id FK
        3. accounts: Bank/Asset accounts
        4. transfers: (Managed via transaction type 'Transfer')
        """
        # Define Tables
        schema_statements = [
            # Categories Table (New)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_categories_id START 1;
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_categories_id'),
                name VARCHAR NOT NULL,
                type VARCHAR(10) NOT NULL, -- 'Income', 'Expense'
                icon_name VARCHAR,         -- Material Icon name
                color VARCHAR,             -- Hex color
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, type)
            )
            """,
            # Accounts Table
            """
            CREATE SEQUENCE IF NOT EXISTS seq_accounts_id START 1;
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_accounts_id'),
                name VARCHAR NOT NULL,
                type VARCHAR(50) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                is_active BOOLEAN DEFAULT TRUE,
                opening_balance DECIMAL(12, 2) DEFAULT 0,
                opening_balance_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Transactions Table (Updated)
            """
            CREATE SEQUENCE IF NOT EXISTS seq_transactions_id START 1;
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_transactions_id'),
                hash_id VARCHAR UNIQUE,    -- Copied from 'hash' logic
                transaction_date DATE NOT NULL,
                amount DECIMAL(12, 2) NOT NULL,
                type VARCHAR(10) NOT NULL, -- 'Income', 'Expense', 'Transfer'
                category_id INTEGER,       -- FK to categories
                account_id INTEGER,        -- FK to accounts
                description VARCHAR,       -- Original description/payee
                note VARCHAR,              -- User notes
                source_file_hash VARCHAR(32),
                reconciled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
            """,
            # Indexes
            "CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(transaction_date)",
            "CREATE INDEX IF NOT EXISTS idx_trans_cat ON transactions(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_trans_acc ON transactions(account_id)"
        ]
        
        try:
            # 1. Check for schema compatibility (Simple migration check)
            try:
                # Check if transactions table exists and has 'category_id'
                result = self._connection.execute("PRAGMA table_info(transactions)").fetchall()
                if result:
                    columns = [r[1] for r in result]
                    if 'category_id' not in columns:
                        logger.warning("Old schema detected! Dropping tables for Realbyte upgrade...")
                        self._connection.execute("DROP TABLE IF EXISTS transactions")
                        self._connection.execute("DROP TABLE IF EXISTS categories")
                        self._connection.execute("DROP TABLE IF EXISTS accounts")
            except Exception as e:
                logger.warning(f"Schema check warning: {e}")

            # 2. Run Schema Statements
            for statement in schema_statements:
                self._connection.execute(statement)
            
            # Seed Default Categories if empty
            self._seed_default_categories()
            
            logger.info("Database schema initialized successfully (Realbyte V1)")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise

    def _seed_default_categories(self):
        """Seed the database with default Realbyte-style categories."""
        defaults = [
            # Expenses
            ("Food", "Expense", "fastfood", "#FF5252"),
            ("Transport", "Expense", "directions_car", "#448AFF"),
            ("Shopping", "Expense", "shopping_cart", "#FF4081"),
            ("Entertainment", "Expense", "movie", "#7C4DFF"),
            ("Housing", "Expense", "home", "#FFC107"),
            ("Utilities", "Expense", "bolt", "#FFC107"),
            ("Health", "Expense", "medical_services", "#00C853"),
            ("Other", "Expense", "more_horiz", "#9E9E9E"),
            # Income
            ("Salary", "Income", "payments", "#4CAF50"),
            ("Part-time", "Income", "watch_later", "#CDDC39"),
            ("Gift", "Income", "card_giftcard", "#E040FB"),
            ("Other", "Income", "attach_money", "#9E9E9E"),
        ]
        
        try:
            with self.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
                if count == 0:
                    # Correct logic
                    data = [(d[0], d[1], d[2], d[3]) for d in defaults]
                    conn.executemany(
                        "INSERT INTO categories (name, type, icon_name, color, is_default) VALUES (?, ?, ?, ?, TRUE)",
                        data
                    )
                    logger.info(f"Seeded {len(defaults)} default categories")
        except Exception as e:
            logger.error(f"Failed to seed categories: {e}")
    
    def get_category_id(self, name: str, type: str = 'Expense') -> int:
        """
        Get category ID by name, creating it if it doesn't exist.
        
        Args:
            name: Category name
            type: Category type (Income/Expense)
            
        Returns:
            Category ID
        """
        try:
            with self.get_connection() as conn:
                # Try to find existing
                result = conn.execute(
                    "SELECT id FROM categories WHERE name = ? AND type = ?", 
                    [name, type]
                ).fetchone()
                
                if result:
                    return result[0]
                
                # Create new if not found
                # Default icon/color based on type
                icon = "attach_money" if type == 'Income' else "payments"
                color = "#4CAF50" if type == 'Income' else "#F44336"
                
                result = conn.execute(
                    """
                    INSERT INTO categories (name, type, icon_name, color)
                    VALUES (?, ?, ?, ?)
                    RETURNING id
                    """,
                    [name, type, icon, color]
                ).fetchone()
                
                logger.info(f"Created new category: {name} ({type})")
                return result[0]
                
        except Exception as e:
            logger.error(f"Failed to get/create category {name}: {e}")
            # Fallback to a default/uncategorized ID if possible, or re-raise
            # For now, let's try to get ID 1 (assuming it exists from seeding)
            return 1
    
    
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
        
        Args:
            hashes: List of transaction hashes to check
        
        Returns:
            Set of existing hashes
        """
        if not hashes:
            return set()
        
        try:
            placeholders = ", ".join(["?" for _ in hashes])
            query = f"SELECT hash_id FROM transactions WHERE hash_id IN ({placeholders})"
            
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
        Retrieve transactions with joined category info.
        """
        # Join with categories to get name, icon, color
        query = """
            SELECT 
                t.*,
                c.name as category_name,
                c.icon_name as category_icon,
                c.color as category_color
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date)
        
        if category:
            query += " AND c.name = ?"
            params.append(category)
        
        if account_id is not None:
            query += " AND t.account_id = ?"
            params.append(account_id)
        
        if reconciled is not None:
            query += " AND t.reconciled = ?"
            params.append(reconciled)
        
        query += f" ORDER BY t.transaction_date DESC LIMIT {limit}"
        
        try:
            with self.get_connection() as conn:
                results = conn.execute(query, params).fetchdf()
                # Rename category_name back to category for compatibility if needed, 
                # or just use new fields. Let's keep 'category' as the name for UI compat.
                df = results.rename(columns={'category_name': 'category'})
                return df.to_dict('records')
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
        
        try:
            with self.get_connection() as conn:
                result = conn.execute(query, params).fetchone()
                net_change = result[0] if result and result[0] is not None else 0
                return float(opening_balance) + float(net_change)
        except Exception as e:
            logger.error(f"Failed to calculate balance: {e}")
            return 0.0

    def create_account(self, name: str, type: str, balance: float = 0.0, currency: str = 'USD') -> Optional[int]:
        """
        Create a new account.
        
        Args:
            name: Account name
            type: Account type (Checking, Savings, etc.)
            balance: Initial opening balance
            currency: Currency code
            
        Returns:
            Account ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO accounts (name, type, opening_balance, currency, is_active)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
            """
            with self.get_connection() as conn:
                result = conn.execute(query, [name, type, balance, currency, True]).fetchone()
                if result:
                    logger.info(f"Created account: {name}")
                    return result[0]
                return None
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            raise

    def update_account(self, account_id: int, name: str, type: str, balance: float, currency: str) -> bool:
        """
        Update an existing account.
        
        Args:
            account_id: ID of account to update
            name: New name
            type: New type
            balance: New opening balance
            currency: New currency
            
        Returns:
            True if successful
        """
        try:
            query = """
                UPDATE accounts 
                SET name = ?, type = ?, opening_balance = ?, currency = ?
                WHERE id = ?
            """
            with self.get_connection() as conn:
                conn.execute(query, [name, type, balance, currency, account_id])
                logger.info(f"Updated account {account_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update account: {e}")
            raise

    def delete_account(self, account_id: int) -> bool:
        """
        Delete an account (soft delete or set transactions to NULL).
        
        Preserves transactions by setting their account_id to NULL.
        
        Args:
            account_id: ID of account to delete
            
        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                # 1. Unlink transactions
                conn.execute("UPDATE transactions SET account_id = NULL WHERE account_id = ?", [account_id])
                
                # 2. Delete account
                conn.execute("DELETE FROM accounts WHERE id = ?", [account_id])
                
                logger.info(f"Deleted account {account_id} and unlinked transactions")
                return True
        except Exception as e:
            logger.error(f"Failed to delete account: {e}")
            raise

    def get_net_worth(self) -> float:
        """
        Calculate total net worth (sum of all account balances).
        
        Returns:
            Total net worth
        """
        try:
            accounts = self.get_all_accounts()
            total = 0.0
            for acc in accounts:
                total += self.calculate_account_balance(acc['id'])
            return total
        except Exception as e:
            logger.error(f"Failed to calculate net worth: {e}")
            return 0.0

    def calculate_account_balance(self, account_id: int, as_of_date: Optional[date] = None) -> float:
        """
        Calculate current balance for an account.
        
        Formula: Opening Balance + Sum(Income) - Sum(Expense) - Sum(Transfers Out)
        
        Args:
            account_id: ID of the account
            as_of_date: Optional date to calculate balance as of (inclusive)
        
        Returns:
            Current balance
        """
        try:
            with self.get_connection() as conn:
                # Get opening balance and date
                account = conn.execute(
                    "SELECT opening_balance, opening_balance_date FROM accounts WHERE id = ?", 
                    [account_id]
                ).fetchone()
                
                if not account:
                    return 0.0
                
                opening_balance = account[0] if account[0] is not None else 0.0
                opening_date = account[1]
                
                # Calculate net movement from transactions
                query = """
                    SELECT 
                        SUM(CASE 
                            WHEN type = 'Income' THEN amount 
                            WHEN type = 'Expense' THEN -amount 
                            WHEN type = 'Transfer' THEN -amount -- Assuming Transfer Out for single-entry
                            ELSE 0 
                        END)
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
                
                result = conn.execute(query, params).fetchone()
                net_change = result[0] if result[0] is not None else 0.0
                
                return float(opening_balance) + float(net_change)
                
        except Exception as e:
            logger.error(f"Failed to calculate account balance: {e}")
            raise
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
