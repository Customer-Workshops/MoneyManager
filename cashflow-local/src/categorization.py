"""
Intelligent Categorization Engine for CashFlow-Local

Implements rule-based transaction categorization with:
- Keyword matching against category_rules.json
- Batch categorization using Pandas vectorized operations
- Dynamic rule learning (save-as-you-go pattern)

Performance: O(n * r) where n=transactions, r=rules
Optimization: Pandas vectorization for large datasets
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

import pandas as pd

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class CategoryEngine:
    """
    Rule-based transaction categorization engine.
    
    Design:
    - Rules stored in JSON file for easy manual editing
    - In-memory cache for fast lookups
    - Case-insensitive substring matching
    
    Performance:
    - Polars for vectorized operations (5x faster than Pandas)
    - Rules cached on first load
    """
    
    def __init__(self, rules_path: str = "/app/category_rules.json"):
        """
        Initialize categorization engine.
        
        Args:
            rules_path: Path to category_rules.json
        """
        self.rules_path = rules_path
        self.rules: List[Dict[str, str]] = []
        self.load_rules()
        logger.info(f"CategoryEngine initialized with {len(self.rules)} rules")
    
    def load_rules(self) -> None:
        """
        Load categorization rules from JSON file.
        
        Creates default file if it doesn't exist.
        """
        try:
            rules_file = Path(self.rules_path)
            
            if not rules_file.exists():
                logger.warning(f"Rules file not found: {self.rules_path}, creating default")
                self._create_default_rules()
            
            with open(self.rules_path, 'r') as f:
                data = json.load(f)
                self.rules = data.get('rules', [])
            
            logger.info(f"Loaded {len(self.rules)} categorization rules")
        
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            self.rules = []
    
    def _create_default_rules(self) -> None:
        """Create default category_rules.json if it doesn't exist."""
        default_rules = {
            "rules": [
                {"keyword": "starbucks", "category": "Coffee"},
                {"keyword": "uber", "category": "Transportation"},
                {"keyword": "amazon", "category": "Shopping"},
                {"keyword": "netflix", "category": "Entertainment"},
                {"keyword": "grocery", "category": "Groceries"},
                {"keyword": "restaurant", "category": "Dining"}
            ]
        }
        
        try:
            Path(self.rules_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.rules_path, 'w') as f:
                json.dump(default_rules, f, indent=2)
            self.rules = default_rules['rules']
            logger.info("Created default category rules")
        except Exception as e:
            logger.error(f"Failed to create default rules: {e}")
    
    def categorize_transaction(self, description: str) -> str:
        """
        Categorize a single transaction based on description.
        
        Algorithm:
        - Case-insensitive substring search
        - First match wins (rules order matters)
        - Returns "Uncategorized" if no match
        
        Args:
            description: Transaction description
        
        Returns:
            Category name
        
        Time Complexity: O(r) where r = number of rules
        """
        description_lower = description.lower()
        
        for rule in self.rules:
            keyword = rule['keyword'].lower()
            if keyword in description_lower:
                logger.debug(f"Matched '{description}' to category '{rule['category']}'")
                return rule['category']
        
        return "Uncategorized"
    
    def categorize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Categorize all transactions in a DataFrame.
        
        Performance: Vectorized using Pandas string operations for better memory efficiency.
        Avoids Pandas → Polars → Pandas conversion overhead.
        
        Args:
            df: DataFrame with 'description' column
        
        Returns:
            DataFrame with 'category' column added/updated
        """
        if df.empty:
            return df
        
        try:
            logger.info(f"Categorizing {len(df)} transactions")
            
            # Initialize category column with 'Uncategorized'
            df['category'] = 'Uncategorized'
            
            # Apply rules in order (first match wins)
            description_lower = df['description'].str.lower()
            
            for rule in self.rules:
                keyword = rule['keyword'].lower()
                category = rule['category']
                
                # Update only uncategorized rows that match this keyword
                mask = (df['category'] == 'Uncategorized') & description_lower.str.contains(keyword, na=False, regex=False)
                df.loc[mask, 'category'] = category
            
            # Log statistics
            category_counts = df['category'].value_counts()
            uncategorized_count = category_counts.get('Uncategorized', 0)
            logger.info(f"Categorization complete: {uncategorized_count} uncategorized, "
                       f"{len(df) - uncategorized_count} categorized")
            
            return df
        
        except Exception as e:
            logger.error(f"Categorization failed: {e}")
            # Fallback: set all to uncategorized
            df['category'] = 'Uncategorized'
            return df
    
    def save_rule(self, keyword: str, category: str) -> bool:
        """
        Add a new categorization rule and persist to JSON.
        
        Args:
            keyword: Keyword to match in transaction descriptions
            category: Category to assign
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if rule already exists
            for rule in self.rules:
                if rule['keyword'].lower() == keyword.lower():
                    logger.info(f"Updating existing rule: {keyword} → {category}")
                    rule['category'] = category
                    self._save_rules_to_file()
                    return True
            
            # Add new rule
            new_rule = {"keyword": keyword, "category": category}
            self.rules.append(new_rule)
            
            self._save_rules_to_file()
            logger.info(f"Added new rule: {keyword} → {category}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save rule: {e}")
            return False
    
    def _save_rules_to_file(self) -> None:
        """Persist current rules to JSON file."""
        try:
            with open(self.rules_path, 'w') as f:
                json.dump({"rules": self.rules}, f, indent=2)
            logger.debug("Rules saved to file")
        except Exception as e:
            logger.error(f"Failed to save rules to file: {e}")
            raise
    
    def update_category_in_db(
        self,
        transaction_ids: List[int],
        new_category: str,
        db_manager: DatabaseManager
    ) -> int:
        """
        Update category for multiple transactions in the database.
        
        Args:
            transaction_ids: List of transaction IDs to update
            new_category: New category to assign
            db_manager: Database connection manager
        
        Returns:
            Number of rows updated
        """
        if not transaction_ids:
            return 0
        
        try:
            placeholders = ", ".join(["?" for _ in transaction_ids])
            update_sql = f"""
                UPDATE transactions 
                SET category = ? 
                WHERE id IN ({placeholders})
            """
            
            with db_manager.get_connection() as conn:
                params = [new_category] + transaction_ids
                conn.execute(update_sql, params)
                logger.info(f"Updated {len(transaction_ids)} transactions to category '{new_category}'")
                return len(transaction_ids)
        
        except Exception as e:
            logger.error(f"Failed to update categories in DB: {e}")
            raise
    
    def get_all_categories(self) -> List[str]:
        """
        Get list of all unique categories from rules.
        
        Returns:
            Sorted list of category names
        """
        categories = set(rule['category'] for rule in self.rules)
        categories.add("Uncategorized")  # Always include
        return sorted(list(categories))


# Global instance
category_engine = CategoryEngine()
