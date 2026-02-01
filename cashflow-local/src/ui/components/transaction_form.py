"""
Manual Transaction Entry Form Component

Provides a form for users to manually add transactions with smart category selection.
"""

import streamlit as st
from datetime import datetime, date, timedelta
import hashlib
import logging
from typing import Optional, Tuple

from src.database import db_manager
from src.ui.utils import get_categories_by_type

logger = logging.getLogger(__name__)


def validate_transaction(
    transaction_date: date,
    description: str,
    amount: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate transaction input.
    
    Args:
        transaction_date: Transaction date
        description: Transaction description
        amount: Transaction amount
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Date validation
    if transaction_date > date.today() + timedelta(days=365):
        return False, "Date cannot be more than 1 year in the future"
    
    # Description validation
    if len(description.strip()) < 3:
        return False, "Description must be at least 3 characters"
    
    # Amount validation
    if amount <= 0:
        return False, "Amount must be a positive number"
    
    return True, None


def save_manual_transaction(
    transaction_date: date,
    description: str,
    amount: float,
    transaction_type: str,
    category: str
) -> Tuple[bool, str]:
    """
    Save a manually entered transaction to the database.
    
    Args:
        transaction_date: Transaction date
        description: Transaction description
        amount: Transaction amount (always positive)
        transaction_type: '💸 Expense', '💰 Income', or '🔄 Transfer'
        category: Category with icon (e.g., '🍔 Food & Dining')
    
    Returns:
        Tuple of (success, message)
    """
    # Map UI type to internal database type
    type_mapping = {
        '💸 Expense': 'Debit',
        '💰 Income': 'Credit',
        '🔄 Transfer': 'Transfer'
    }
    internal_type = type_mapping.get(transaction_type, 'Debit')
    
    # Remove icon from category for database storage
    category_clean = category.split(' ', 1)[1] if ' ' in category else category
    
    # Generate hash for deduplication
    hash_string = f"{transaction_date}_{description}_{amount}_{internal_type}"
    transaction_hash = hashlib.md5(hash_string.encode()).hexdigest()
    
    try:
        # Check for duplicates
        existing_hashes = db_manager.check_duplicates([transaction_hash])
        if transaction_hash in existing_hashes:
            return False, "This transaction already exists (duplicate detected)"
        
        # Insert transaction
        with db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO transactions (
                    hash, transaction_date, description, 
                    amount, type, category, source_file_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction_hash,
                transaction_date,
                description,
                amount,
                internal_type,
                category_clean,
                'MANUAL_ENTRY'  # Special marker for manual transactions
            ))
        
        logger.info(f"Manual transaction saved: {description} - ${amount}")
        return True, f"✅ {transaction_type} saved: ${amount:,.2f}"
    
    except Exception as e:
        logger.error(f"Failed to save manual transaction: {e}")
        return False, f"Failed to save transaction: {str(e)}"


def render_transaction_form(location: str = "inline"):
    """
    Render manual transaction entry form.
    
    Args:
        location: 'sidebar', 'inline', or 'modal' (currently only 'inline' supported)
    """
    st.subheader("➕ Add Transaction")
    
    with st.form("add_transaction_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            transaction_date = st.date_input(
                "Date",
                value=date.today(),
                max_value=date.today() + timedelta(days=365),
                help="Transaction date (cannot be more than 1 year in the future)"
            )
        
        with col2:
            transaction_type = st.selectbox(
                "Type",
                ["💸 Expense", "💰 Income", "🔄 Transfer"],
                index=0,
                help="Select transaction type"
            )
        
        amount = st.number_input(
            "Amount ($)",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            help="Enter amount (always positive)"
        )
        
        description = st.text_input(
            "Description",
            placeholder="e.g., Coffee at Starbucks",
            help="Transaction description (minimum 3 characters)"
        )
        
        # Get categories filtered by type
        categories = get_categories_by_type(transaction_type)
        category = st.selectbox(
            "Category",
            categories,
            index=0,
            help="Select a category for this transaction"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Save Transaction", type="primary", use_container_width=True)
        with col2:
            cleared = st.form_submit_button("🗑️ Clear", use_container_width=True)
        
        if submitted:
            # Validate transaction
            is_valid, error_msg = validate_transaction(transaction_date, description, amount)
            
            if not is_valid:
                st.error(f"❌ {error_msg}")
            else:
                # Save transaction
                success, message = save_manual_transaction(
                    date=transaction_date,
                    description=description,
                    amount=amount,
                    transaction_type=transaction_type,
                    category=category
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                    # Refresh the page to show updated data
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        if cleared:
            st.info("Form cleared. Ready for new entry.")
