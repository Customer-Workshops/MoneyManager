"""
Reconciliation Logic for CashFlow-Local

Provides balance reconciliation, duplicate detection, and variance analysis
to help users ensure their app data matches actual bank balances.

Author: Antigravity AI
License: MIT
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """
    Engine for bank account reconciliation and balance tracking.
    
    Features:
    - Balance variance detection
    - Duplicate transaction detection
    - Missing transaction suggestions
    - Reconciliation reporting
    """
    
    def __init__(self, db_manager):
        """
        Initialize reconciliation engine.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    def detect_duplicates(
        self,
        account_id: int,
        threshold_days: int = 3,
        amount_tolerance: float = 0.01
    ) -> List[Dict[str, Any]]:
        """
        Detect potential duplicate transactions.
        
        A transaction is considered a potential duplicate if:
        - Same amount (within tolerance)
        - Similar description (Levenshtein distance)
        - Within threshold_days of each other
        
        Args:
            account_id: Account ID to check
            threshold_days: Number of days to consider for duplicates
            amount_tolerance: Amount difference tolerance
        
        Returns:
            List of potential duplicate pairs
        """
        try:
            # Get all transactions for the account
            transactions = self.db_manager.get_transactions(
                account_id=account_id,
                limit=10000
            )
            
            duplicates = []
            checked_pairs = set()
            
            for i, txn1 in enumerate(transactions):
                for txn2 in transactions[i+1:]:
                    # Skip if already checked
                    pair_key = tuple(sorted([txn1['id'], txn2['id']]))
                    if pair_key in checked_pairs:
                        continue
                    
                    # Check if amounts match
                    amount_diff = abs(txn1['amount'] - txn2['amount'])
                    if amount_diff > amount_tolerance:
                        continue
                    
                    # Check if dates are within threshold
                    date1 = txn1['transaction_date']
                    date2 = txn2['transaction_date']
                    
                    if isinstance(date1, str):
                        date1 = datetime.strptime(date1, '%Y-%m-%d').date()
                    if isinstance(date2, str):
                        date2 = datetime.strptime(date2, '%Y-%m-%d').date()
                    
                    date_diff = abs((date1 - date2).days)
                    if date_diff > threshold_days:
                        continue
                    
                    # Check if descriptions are similar
                    desc1 = txn1['description'].lower()
                    desc2 = txn2['description'].lower()
                    similarity = self._calculate_similarity(desc1, desc2)
                    
                    if similarity > 0.7:  # 70% similarity threshold
                        duplicates.append({
                            'transaction1': txn1,
                            'transaction2': txn2,
                            'similarity': similarity,
                            'amount_diff': amount_diff,
                            'date_diff': date_diff
                        })
                        checked_pairs.add(pair_key)
            
            logger.info(f"Found {len(duplicates)} potential duplicate pairs")
            return duplicates
        
        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            raise
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using simple ratio.
        
        Args:
            str1: First string
            str2: Second string
        
        Returns:
            Similarity score between 0 and 1
        """
        # Simple character-based similarity
        if not str1 or not str2:
            return 0.0
        
        # Count matching characters
        str1_chars = set(str1)
        str2_chars = set(str2)
        
        intersection = str1_chars & str2_chars
        union = str1_chars | str2_chars
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def analyze_variance(
        self,
        account_id: int,
        statement_date: datetime,
        statement_balance: float
    ) -> Dict[str, Any]:
        """
        Analyze variance between calculated and actual balance.
        
        Args:
            account_id: Account ID
            statement_date: Date of the bank statement
            statement_balance: Balance shown on bank statement
        
        Returns:
            Dictionary with variance analysis
        """
        try:
            # Calculate expected balance
            calculated_balance = self.db_manager.calculate_account_balance(
                account_id=account_id,
                as_of_date=statement_date
            )
            
            variance = statement_balance - calculated_balance
            variance_pct = (variance / statement_balance * 100) if statement_balance != 0 else 0
            
            # Get unreconciled transactions around the statement date
            unreconciled = self.db_manager.get_transactions(
                account_id=account_id,
                end_date=statement_date,
                reconciled=False,
                limit=100
            )
            
            analysis = {
                'calculated_balance': calculated_balance,
                'statement_balance': statement_balance,
                'variance': variance,
                'variance_percentage': variance_pct,
                'is_reconciled': abs(variance) < 0.01,
                'unreconciled_count': len(unreconciled),
                'unreconciled_transactions': unreconciled,
                'statement_date': statement_date
            }
            
            logger.info(f"Variance analysis: ${variance:.2f} ({variance_pct:.2f}%)")
            return analysis
        
        except Exception as e:
            logger.error(f"Variance analysis failed: {e}")
            raise
    
    def suggest_missing_transactions(
        self,
        account_id: int,
        start_date: datetime,
        end_date: datetime,
        expected_balance: float
    ) -> List[str]:
        """
        Suggest possible missing transactions based on balance gap.
        
        Args:
            account_id: Account ID
            start_date: Period start date
            end_date: Period end date
            expected_balance: Expected ending balance
        
        Returns:
            List of suggestions
        """
        try:
            calculated_balance = self.db_manager.calculate_account_balance(
                account_id=account_id,
                as_of_date=end_date
            )
            
            gap = expected_balance - calculated_balance
            suggestions = []
            
            if abs(gap) < 0.01:
                suggestions.append("✅ Balance matches! No missing transactions detected.")
            elif gap > 0:
                suggestions.append(f"💰 Missing income/credit of ${gap:.2f}")
                suggestions.append("Check for:")
                suggestions.append("  - Deposits not recorded")
                suggestions.append("  - Refunds or credits")
                suggestions.append("  - Interest payments")
            else:
                suggestions.append(f"💸 Missing expense/debit of ${abs(gap):.2f}")
                suggestions.append("Check for:")
                suggestions.append("  - Pending transactions")
                suggestions.append("  - Bank fees or charges")
                suggestions.append("  - Automated payments")
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Missing transaction suggestion failed: {e}")
            raise
    
    def generate_reconciliation_report(
        self,
        account_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate comprehensive reconciliation report.
        
        Args:
            account_id: Account ID
            start_date: Period start date
            end_date: Period end date
        
        Returns:
            Reconciliation report dictionary
        """
        try:
            account = self.db_manager.get_account_by_id(account_id)
            
            # Get transactions for the period
            all_transactions = self.db_manager.get_transactions(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            reconciled_txns = [t for t in all_transactions if t.get('reconciled', False)]
            unreconciled_txns = [t for t in all_transactions if not t.get('reconciled', False)]
            
            # Calculate balances
            opening_balance = self.db_manager.calculate_account_balance(
                account_id=account_id,
                as_of_date=start_date
            )
            closing_balance = self.db_manager.calculate_account_balance(
                account_id=account_id,
                as_of_date=end_date
            )
            
            # Get balance history
            balance_history = self.db_manager.get_balance_history(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date
            )
            
            report = {
                'account': account,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'opening_balance': opening_balance,
                    'closing_balance': closing_balance,
                    'net_change': closing_balance - opening_balance,
                    'total_transactions': len(all_transactions),
                    'reconciled_count': len(reconciled_txns),
                    'unreconciled_count': len(unreconciled_txns),
                    'reconciliation_percentage': (len(reconciled_txns) / len(all_transactions) * 100) if all_transactions else 0
                },
                'transactions': {
                    'all': all_transactions,
                    'reconciled': reconciled_txns,
                    'unreconciled': unreconciled_txns
                },
                'balance_history': balance_history
            }
            
            logger.info(f"Generated reconciliation report for account {account_id}")
            return report
        
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise
