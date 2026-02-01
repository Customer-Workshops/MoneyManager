"""
Bill Management Module for CashFlow-Local

Provides functionality for managing bill reminders and payment alerts.
Supports recurring bills, payment tracking, and notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.database import db_manager

logger = logging.getLogger(__name__)


class BillManager:
    """
    Manages bill reminders and payment alerts.
    
    Features:
    - Add/update/delete bills
    - Track recurring bills (monthly, quarterly, yearly)
    - Get upcoming and overdue bills
    - Mark bills as paid
    - Calculate next due dates for recurring bills
    """
    
    # Supported bill types
    BILL_TYPES = [
        "Rent",
        "Electricity",
        "Water",
        "Gas",
        "Internet",
        "Mobile",
        "Netflix",
        "Spotify",
        "Other Subscriptions",
        "Insurance Premium",
        "Loan EMI",
        "Credit Card",
        "Other"
    ]
    
    # Recurrence patterns
    RECURRENCE_TYPES = [
        "One-time",
        "Monthly",
        "Quarterly",
        "Half-yearly",
        "Yearly"
    ]
    
    # Bill status
    STATUS_TYPES = [
        "pending",
        "paid",
        "overdue"
    ]
    
    @staticmethod
    def add_bill(
        name: str,
        bill_type: str,
        amount: float,
        due_date: datetime,
        recurrence: str = "Monthly",
        reminder_days: int = 3,
        notes: str = ""
    ) -> bool:
        """
        Add a new bill to the system.
        
        Args:
            name: Bill name/description
            bill_type: Type of bill (from BILL_TYPES)
            amount: Bill amount
            due_date: Due date for payment
            recurrence: Recurrence pattern (from RECURRENCE_TYPES)
            reminder_days: Days before due date to remind
            notes: Additional notes
        
        Returns:
            True if successful, False otherwise
        """
        try:
            insert_query = """
                INSERT INTO bills (
                    name, bill_type, amount, due_date, recurrence,
                    reminder_days, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """
            
            with db_manager.get_connection() as conn:
                conn.execute(
                    insert_query,
                    (name, bill_type, amount, due_date, recurrence, reminder_days, notes)
                )
            
            logger.info(f"Added bill: {name} ({bill_type}) - ${amount}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add bill: {e}")
            return False
    
    @staticmethod
    def get_all_bills() -> List[Dict[str, Any]]:
        """
        Retrieve all bills from the database.
        
        Returns:
            List of bill dictionaries
        """
        try:
            query = """
                SELECT 
                    id, name, bill_type, amount, due_date, recurrence,
                    reminder_days, status, notes, last_paid_date,
                    created_at, updated_at
                FROM bills
                ORDER BY due_date ASC
            """
            
            with db_manager.get_connection() as conn:
                results = conn.execute(query).fetchdf()
                return results.to_dict('records')
        
        except Exception as e:
            logger.error(f"Failed to retrieve bills: {e}")
            return []
    
    @staticmethod
    def get_upcoming_bills(days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Get bills due in the next N days.
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List of upcoming bills
        """
        try:
            today = datetime.now().date()
            future_date = today + timedelta(days=days_ahead)
            
            query = """
                SELECT 
                    id, name, bill_type, amount, due_date, recurrence,
                    reminder_days, status, notes
                FROM bills
                WHERE due_date >= ? AND due_date <= ?
                AND status != 'paid'
                ORDER BY due_date ASC
            """
            
            with db_manager.get_connection() as conn:
                results = conn.execute(query, (today, future_date)).fetchdf()
                return results.to_dict('records')
        
        except Exception as e:
            logger.error(f"Failed to retrieve upcoming bills: {e}")
            return []
    
    @staticmethod
    def get_overdue_bills() -> List[Dict[str, Any]]:
        """
        Get all overdue bills (past due date and not paid).
        
        Returns:
            List of overdue bills
        """
        try:
            today = datetime.now().date()
            
            query = """
                SELECT 
                    id, name, bill_type, amount, due_date, recurrence,
                    reminder_days, status, notes
                FROM bills
                WHERE due_date < ?
                AND status = 'pending'
                ORDER BY due_date ASC
            """
            
            with db_manager.get_connection() as conn:
                results = conn.execute(query, (today,)).fetchdf()
                # Update status to overdue
                for bill in results.to_dict('records'):
                    BillManager._update_bill_status(bill['id'], 'overdue')
                
                # Fetch again to get updated status
                results = conn.execute(query.replace("status = 'pending'", "status = 'overdue'"), (today,)).fetchdf()
                return results.to_dict('records')
        
        except Exception as e:
            logger.error(f"Failed to retrieve overdue bills: {e}")
            return []
    
    @staticmethod
    def get_bills_needing_reminder() -> List[Dict[str, Any]]:
        """
        Get bills that need reminders (within reminder_days of due date).
        
        Returns:
            List of bills needing reminders
        """
        try:
            query = """
                SELECT 
                    id, name, bill_type, amount, due_date, recurrence,
                    reminder_days, status, notes
                FROM bills
                WHERE due_date - CURRENT_DATE <= reminder_days
                AND due_date >= CURRENT_DATE
                AND status = 'pending'
                ORDER BY due_date ASC
            """
            
            with db_manager.get_connection() as conn:
                results = conn.execute(query).fetchdf()
                return results.to_dict('records')
        
        except Exception as e:
            logger.error(f"Failed to retrieve bills needing reminder: {e}")
            return []
    
    @staticmethod
    def mark_bill_paid(bill_id: int, payment_date: Optional[datetime] = None) -> bool:
        """
        Mark a bill as paid and handle recurrence.
        
        Args:
            bill_id: ID of the bill to mark as paid
            payment_date: Date of payment (defaults to today)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if payment_date is None:
                payment_date = datetime.now().date()
            
            # Get bill details
            bill = BillManager._get_bill_by_id(bill_id)
            if not bill:
                logger.error(f"Bill {bill_id} not found")
                return False
            
            # Update bill status and last paid date
            update_query = """
                UPDATE bills
                SET status = 'paid',
                    last_paid_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            with db_manager.get_connection() as conn:
                conn.execute(update_query, (payment_date, bill_id))
            
            # Handle recurring bills
            if bill['recurrence'] != 'One-time':
                next_due_date = BillManager._calculate_next_due_date(
                    bill['due_date'],
                    bill['recurrence']
                )
                
                # Create a new bill for the next occurrence
                BillManager.add_bill(
                    name=bill['name'],
                    bill_type=bill['bill_type'],
                    amount=bill['amount'],
                    due_date=next_due_date,
                    recurrence=bill['recurrence'],
                    reminder_days=bill['reminder_days'],
                    notes=bill.get('notes', '')
                )
            
            logger.info(f"Marked bill {bill_id} as paid on {payment_date}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark bill as paid: {e}")
            return False
    
    @staticmethod
    def update_bill(
        bill_id: int,
        name: Optional[str] = None,
        bill_type: Optional[str] = None,
        amount: Optional[float] = None,
        due_date: Optional[datetime] = None,
        recurrence: Optional[str] = None,
        reminder_days: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update bill details.
        
        Args:
            bill_id: ID of the bill to update
            name: Updated bill name
            bill_type: Updated bill type
            amount: Updated amount
            due_date: Updated due date
            recurrence: Updated recurrence
            reminder_days: Updated reminder days
            notes: Updated notes
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update query dynamically based on provided fields
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if bill_type is not None:
                updates.append("bill_type = ?")
                params.append(bill_type)
            if amount is not None:
                updates.append("amount = ?")
                params.append(amount)
            if due_date is not None:
                updates.append("due_date = ?")
                params.append(due_date)
            if recurrence is not None:
                updates.append("recurrence = ?")
                params.append(recurrence)
            if reminder_days is not None:
                updates.append("reminder_days = ?")
                params.append(reminder_days)
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)
            
            if not updates:
                return True  # Nothing to update
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(bill_id)
            
            update_query = f"""
                UPDATE bills
                SET {', '.join(updates)}
                WHERE id = ?
            """
            
            with db_manager.get_connection() as conn:
                conn.execute(update_query, params)
            
            logger.info(f"Updated bill {bill_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update bill: {e}")
            return False
    
    @staticmethod
    def delete_bill(bill_id: int) -> bool:
        """
        Delete a bill from the system.
        
        Args:
            bill_id: ID of the bill to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            delete_query = "DELETE FROM bills WHERE id = ?"
            
            with db_manager.get_connection() as conn:
                conn.execute(delete_query, (bill_id,))
            
            logger.info(f"Deleted bill {bill_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete bill: {e}")
            return False
    
    @staticmethod
    def get_total_bills_this_month() -> float:
        """
        Calculate total amount of bills due this month.
        
        Returns:
            Total bill amount for current month
        """
        try:
            today = datetime.now().date()
            start_of_month = today.replace(day=1)
            
            # Calculate end of month
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
            query = """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM bills
                WHERE due_date >= ? AND due_date <= ?
            """
            
            with db_manager.get_connection() as conn:
                result = conn.execute(query, (start_of_month, end_of_month)).fetchone()
                return float(result[0]) if result else 0.0
        
        except Exception as e:
            logger.error(f"Failed to calculate total bills: {e}")
            return 0.0
    
    @staticmethod
    def get_payment_history(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get payment history (paid bills).
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of paid bills
        """
        try:
            query = f"""
                SELECT 
                    id, name, bill_type, amount, due_date, last_paid_date,
                    recurrence, notes
                FROM bills
                WHERE status = 'paid'
                ORDER BY last_paid_date DESC
                LIMIT {limit}
            """
            
            with db_manager.get_connection() as conn:
                results = conn.execute(query).fetchdf()
                return results.to_dict('records')
        
        except Exception as e:
            logger.error(f"Failed to retrieve payment history: {e}")
            return []
    
    # Helper methods
    
    @staticmethod
    def _get_bill_by_id(bill_id: int) -> Optional[Dict[str, Any]]:
        """Get bill details by ID."""
        try:
            query = """
                SELECT 
                    id, name, bill_type, amount, due_date, recurrence,
                    reminder_days, status, notes, last_paid_date
                FROM bills
                WHERE id = ?
            """
            
            with db_manager.get_connection() as conn:
                result = conn.execute(query, (bill_id,)).fetchone()
                
                if result:
                    columns = ['id', 'name', 'bill_type', 'amount', 'due_date', 
                             'recurrence', 'reminder_days', 'status', 'notes', 'last_paid_date']
                    return dict(zip(columns, result))
                return None
        
        except Exception as e:
            logger.error(f"Failed to get bill {bill_id}: {e}")
            return None
    
    @staticmethod
    def _update_bill_status(bill_id: int, status: str) -> bool:
        """Update bill status."""
        try:
            update_query = """
                UPDATE bills
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            with db_manager.get_connection() as conn:
                conn.execute(update_query, (status, bill_id))
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update bill status: {e}")
            return False
    
    @staticmethod
    def _calculate_next_due_date(current_due_date, recurrence: str) -> datetime:
        """
        Calculate next due date based on recurrence pattern.
        
        Args:
            current_due_date: Current due date (can be date or datetime)
            recurrence: Recurrence pattern
        
        Returns:
            Next due date
        """
        # Convert to date if datetime
        if isinstance(current_due_date, datetime):
            current_due_date = current_due_date.date()
        
        if recurrence == "Monthly":
            # Add one month
            if current_due_date.month == 12:
                next_date = current_due_date.replace(year=current_due_date.year + 1, month=1)
            else:
                next_date = current_due_date.replace(month=current_due_date.month + 1)
        
        elif recurrence == "Quarterly":
            # Add three months
            new_month = current_due_date.month + 3
            year_increment = (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            next_date = current_due_date.replace(
                year=current_due_date.year + year_increment,
                month=new_month
            )
        
        elif recurrence == "Half-yearly":
            # Add six months
            new_month = current_due_date.month + 6
            year_increment = (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            next_date = current_due_date.replace(
                year=current_due_date.year + year_increment,
                month=new_month
            )
        
        elif recurrence == "Yearly":
            # Add one year
            next_date = current_due_date.replace(year=current_due_date.year + 1)
        
        else:  # One-time
            next_date = current_due_date
        
        return datetime.combine(next_date, datetime.min.time())


# Global instance
bill_manager = BillManager()
