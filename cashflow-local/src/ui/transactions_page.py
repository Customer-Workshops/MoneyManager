"""
Transactions Page for CashFlow-Local Streamlit App

Displays searchable/filterable transaction table with bulk category editing.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging

from src.database import db_manager
from src.categorization import category_engine
from src.ui.utils import get_type_icon

logger = logging.getLogger(__name__)


def render_transactions_page():
    """
    Render the transactions management page.
    
    Features:
    - Searchable transaction table
    - Filters (date range, category, amount)
    - Bulk category editing
    - Save-as-rule functionality
    """
    st.header("💳 Transactions")
    
    # Filters
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            date_range = st.date_input(
                "Date Range",
                value=(start_date, end_date),
                help="Filter transactions by date range"
            )
        
        with col2:
            # Category filter
            all_categories = category_engine.get_all_categories()
            selected_category = st.selectbox(
                "Category",
                options=["All"] + all_categories,
                help="Filter by category"
            )
        
        with col3:
            # Search
            search_query = st.text_input(
                "Search Description",
                placeholder="e.g., Starbucks",
                help="Search in transaction descriptions"
            )
    
    # Fetch transactions
    try:
        query = "SELECT id, transaction_date, description, amount, type, category FROM transactions WHERE 1=1"
        params = []
        
        # Apply date filter
        if len(date_range) == 2:
            query += " AND transaction_date >= ? AND transaction_date <= ?"
            params.extend(date_range)
        
        # Apply category filter
        if selected_category != "All":
            query += " AND category = ?"
            params.append(selected_category)
        
        # Apply search filter
        if search_query:
            query += " AND LOWER(description) LIKE ?"
            params.append(f"%{search_query.lower()}%")
        
        query += " ORDER BY transaction_date DESC LIMIT 500"
        
        results = db_manager.execute_query(query, tuple(params) if params else None)
        
        if not results:
            st.info("No transactions found matching your filters")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(
            results,
            columns=['id', 'transaction_date', 'description', 'amount', 'type', 'category']
        )
        
        # Format for display
        df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d')
        df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
        
        # Add icon to type column
        df['type'] = df['type'].apply(lambda x: f"{get_type_icon(x)} {x}")
        
        st.success(f"Found {len(df)} transactions")
        
        # Editable data editor
        st.subheader("Edit Categories")
        st.markdown("""
        **Instructions:**
        1. Click on a cell in the Category column to edit
        2. Change categories as needed
        3. Click "Save Changes" below
        4. Optionally save your edits as permanent rules
        """)
        
        edited_df = st.data_editor(
            df,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "transaction_date": st.column_config.TextColumn("Date", disabled=True),
                "description": st.column_config.TextColumn("Description", disabled=True, width="large"),
                "amount": st.column_config.TextColumn("Amount", disabled=True),
                "type": st.column_config.TextColumn("Type", disabled=True),
                "category": st.column_config.SelectboxColumn(
                    "Category",
                    options=all_categories,
                    required=True
                )
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key="transaction_editor"
        )
        
        # Detect changes
        changes = []
        for idx in range(len(df)):
            if df.iloc[idx]['category'] != edited_df.iloc[idx]['category']:
                changes.append({
                    'id': int(edited_df.iloc[idx]['id']),
                    'description': edited_df.iloc[idx]['description'],
                    'old_category': df.iloc[idx]['category'],
                    'new_category': edited_df.iloc[idx]['category']
                })
        
        if changes:
            st.warning(f"⚠️ {len(changes)} changes detected")
            
            # Show changes
            with st.expander(f"View {len(changes)} Changes"):
                for change in changes:
                    st.markdown(
                        f"- **{change['description'][:50]}...**: "
                        f"`{change['old_category']}` → `{change['new_category']}`"
                    )
            
            # Save options
            col1, col2 = st.columns([3, 1])
            
            with col1:
                save_as_rules = st.checkbox(
                    "💾 Save these categorizations as permanent rules",
                    help="Future transactions with similar descriptions will be automatically categorized"
                )
            
            with col2:
                if st.button("✅ Save Changes", type="primary"):
                    try:
                        # Update categories in database
                        for change in changes:
                            category_engine.update_category_in_db(
                                [change['id']],
                                change['new_category'],
                                db_manager
                            )
                            
                            # Save as rule if requested
                            if save_as_rules:
                                # Extract keyword (first word of description)
                                keyword = change['description'].split()[0].lower()
                                category_engine.save_rule(keyword, change['new_category'])
                        
                        st.success(f"✅ Updated {len(changes)} transactions!")
                        if save_as_rules:
                            st.success(f"💾 Saved {len(changes)} new categorization rules!")
                        
                        # Refresh
                        st.rerun()
                    
                    except Exception as e:
                        logger.error(f"Failed to save changes: {e}")
                        st.error(f"Failed to save changes: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to load transactions: {e}")
        st.error(f"Failed to load transactions: {str(e)}")
