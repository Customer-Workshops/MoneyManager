"""
Transactions Page for CashFlow-Local Streamlit App

Displays searchable/filterable transaction table with bulk category editing.
Features advanced search with fuzzy matching, regex support, tags, and saved searches.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
import json

from src.database import db_manager
from src.categorization import category_engine
from src.ui.utils import get_type_icon
from src.ui.components.transaction_form import render_transaction_form

logger = logging.getLogger(__name__)

# Constants
DEFAULT_FUZZY_THRESHOLD = 0.6


def render_transactions_page():
    """
    Render the transactions management page.
    
    Features:
    - Manual transaction entry form
    - Searchable transaction table
    - Filters (date range, category, amount)
    - Bulk category editing
    - Save-as-rule functionality
    """
    st.header("💳 Transactions")
    
    # Manual transaction entry form at top
    with st.expander("➕ Add New Transaction", expanded=False):
        render_transaction_form()
    
    st.divider()
    
    # Filters
    with st.expander("🔍 Advanced Filters", expanded=True):
        # Row 1: Date and Amount filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range presets
            date_preset = st.selectbox(
                "Date Range Preset",
                options=["Custom", "Last 7 Days", "Last 30 Days", "Last 90 Days", "This Month", "Last Month", "This Year"],
                help="Quick date range selection"
            )
            
            # Calculate date range based on preset
            end_date = datetime.now().date()
            if date_preset == "Last 7 Days":
                start_date = end_date - timedelta(days=7)
            elif date_preset == "Last 30 Days":
                start_date = end_date - timedelta(days=30)
            elif date_preset == "Last 90 Days":
                start_date = end_date - timedelta(days=90)
            elif date_preset == "This Month":
                start_date = end_date.replace(day=1)
            elif date_preset == "Last Month":
                first_of_this_month = end_date.replace(day=1)
                end_date = first_of_this_month - timedelta(days=1)
                start_date = end_date.replace(day=1)
            elif date_preset == "This Year":
                start_date = end_date.replace(month=1, day=1)
            else:  # Custom
                start_date = end_date - timedelta(days=30)
            
            # Allow custom date input
            if date_preset == "Custom":
                date_range = st.date_input(
                    "Custom Date Range",
                    value=(start_date, end_date),
                    help="Select custom date range"
                )
            else:
                st.info(f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                date_range = (start_date, end_date)
        
        with col2:
            # Amount range filter
            st.subheader("Amount Range")
            col2a, col2b = st.columns(2)
            with col2a:
                min_amount = st.number_input(
                    "Min Amount ($)",
                    min_value=0.0,
                    value=0.0,
                    step=10.0,
                    help="Minimum transaction amount"
                )
            with col2b:
                max_amount = st.number_input(
                    "Max Amount ($)",
                    min_value=0.0,
                    value=0.0,
                    step=10.0,
                    help="Maximum transaction amount (0 = no limit)"
                )
        
        with col3:
            # Transaction type filter
            transaction_type = st.multiselect(
                "Transaction Type",
                options=["Credit", "Debit", "Transfer"],
                default=["Credit", "Debit", "Transfer"],
                help="Filter by transaction type"
            )
        
        # Row 2: Category and Search filters
        col4, col5 = st.columns(2)
        
        with col4:
            # Category filter - multi-select
            all_categories = category_engine.get_all_categories()
            selected_categories = st.multiselect(
                "Categories",
                options=all_categories,
                default=[],
                help="Filter by multiple categories (leave empty for all)"
            )
        
        with col5:
            # Search with advanced options
            search_query = st.text_input(
                "Search Description/Merchant",
                placeholder="e.g., Starbucks, Amazon",
                help="Search in transaction descriptions"
            )
            
            # Advanced search options
            col5a, col5b, col5c = st.columns(3)
            with col5a:
                use_fuzzy = st.checkbox("🔤 Fuzzy Search", help="Handle typos and similar spellings")
            with col5b:
                use_regex = st.checkbox("🔧 Regex", help="Use regular expressions for advanced patterns")
            with col5c:
                fuzzy_threshold = DEFAULT_FUZZY_THRESHOLD
                if use_fuzzy:
                    fuzzy_threshold = st.slider("Similarity", 0.5, 1.0, DEFAULT_FUZZY_THRESHOLD, 0.05, key="fuzzy_slider")
        
        # Row 3: Tags filter
        st.markdown("---")
        col_tags1, col_tags2 = st.columns(2)
        
        with col_tags1:
            # Tags filter
            all_tags = db_manager.get_all_tags()
            tag_names = [tag['name'] for tag in all_tags]
            selected_tags = st.multiselect(
                "🏷️ Filter by Tags",
                options=tag_names,
                default=[],
                help="Filter transactions by tags"
            )
        
        with col_tags2:
            # Save search option
            save_search_name = st.text_input(
                "💾 Save Current Filters As",
                placeholder="e.g., Monthly Coffee Expenses",
                help="Save current filter configuration for quick access"
            )
            if save_search_name and st.button("Save Search"):
                # Build filter config
                filter_config = {
                    "date_preset": date_preset,
                    "date_range": [str(date_range[0]), str(date_range[1])] if len(date_range) == 2 else [],
                    "categories": selected_categories,
                    "transaction_type": transaction_type,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "search_query": search_query,
                    "tags": selected_tags,
                    "use_fuzzy": use_fuzzy,
                    "use_regex": use_regex
                }
                
                if db_manager.save_search(save_search_name, json.dumps(filter_config)):
                    st.success(f"✅ Saved search '{save_search_name}'")
                    st.rerun()
                else:
                    st.error("Failed to save search")
        
        # Row 4: Filter actions
        col6, col7, col8 = st.columns([1, 1, 1])
        with col6:
            if st.button("🗑️ Clear All Filters"):
                st.rerun()
        with col7:
            # Filter count will be shown after applying filters
            pass
        with col8:
            pass
    
    # Fetch transactions
    try:
        # Base query with tag support
        if selected_tags:
            query = """
                SELECT DISTINCT t.id, t.transaction_date, t.description, t.amount, t.type, t.category 
                FROM transactions t
                JOIN transaction_tags tt ON t.id = tt.transaction_id
                JOIN tags tg ON tt.tag_id = tg.id
                WHERE 1=1
            """
        else:
            query = "SELECT id, transaction_date, description, amount, type, category FROM transactions WHERE 1=1"
        
        params = []
        
        # Apply tags filter
        if selected_tags:
            # Get tag IDs
            tag_ids = [tag['id'] for tag in all_tags if tag['name'] in selected_tags]
            if tag_ids:
                placeholders = ", ".join(["?" for _ in tag_ids])
                query += f" AND tg.id IN ({placeholders})"
                params.extend(tag_ids)
        
        # Apply date filter
        if len(date_range) == 2:
            prefix = "t." if selected_tags else ""
            query += f" AND {prefix}transaction_date >= ? AND {prefix}transaction_date <= ?"
            params.extend(date_range)
        
        # Apply category filter (multi-select)
        if selected_categories:
            prefix = "t." if selected_tags else ""
            placeholders = ", ".join(["?" for _ in selected_categories])
            query += f" AND {prefix}category IN ({placeholders})"
            params.extend(selected_categories)
        
        # Apply transaction type filter
        if transaction_type:
            prefix = "t." if selected_tags else ""
            placeholders = ", ".join(["?" for _ in transaction_type])
            query += f" AND {prefix}type IN ({placeholders})"
            params.extend(transaction_type)
        
        # Apply amount range filter
        if min_amount > 0:
            prefix = "t." if selected_tags else ""
            query += f" AND ABS({prefix}amount) >= ?"
            params.append(min_amount)
        
        if max_amount > 0:
            prefix = "t." if selected_tags else ""
            query += f" AND ABS({prefix}amount) <= ?"
            params.append(max_amount)
        
        # For fuzzy/regex search, we'll do post-processing
        # For exact search, use SQL LIKE
        if search_query and not use_fuzzy and not use_regex:
            prefix = "t." if selected_tags else ""
            query += f" AND LOWER({prefix}description) LIKE ?"
            params.append(f"%{search_query.lower()}%")
        
        prefix = "t." if selected_tags else ""
        query += f" ORDER BY {prefix}transaction_date DESC LIMIT 1000"
        
        results = db_manager.execute_query(query, tuple(params) if params else None)
        
        if not results:
            st.info("🔍 No transactions found matching your filters")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(
            results,
            columns=['id', 'transaction_date', 'description', 'amount', 'type', 'category']
        )
        
        # Apply fuzzy or regex search post-processing if needed
        if search_query and (use_fuzzy or use_regex):
            # Convert to dict for filtering
            transactions = df.to_dict('records')
            
            # Determine search mode
            if use_fuzzy:
                search_mode = 'fuzzy'
            elif use_regex:
                search_mode = 'regex'
            else:
                search_mode = 'exact'
            
            # Apply search filter
            filtered_transactions = filter_by_search(
                transactions,
                search_query,
                search_mode,
                fuzzy_threshold if use_fuzzy else DEFAULT_FUZZY_THRESHOLD
            )
            
            # Convert back to DataFrame
            if filtered_transactions:
                df = pd.DataFrame(filtered_transactions)
            else:
                st.info(f"🔍 No transactions found matching '{search_query}' with {search_mode} search")
                return
        
        # Show active filters summary
        active_filters = []
        if len(date_range) == 2:
            active_filters.append(f"📅 Date: {date_range[0]} to {date_range[1]}")
        if selected_categories:
            active_filters.append(f"🏷️ Categories: {', '.join(selected_categories)}")
        if transaction_type and len(transaction_type) < 3:
            active_filters.append(f"💳 Type: {', '.join(transaction_type)}")
        if min_amount > 0 or max_amount > 0:
            amount_filter = "💰 Amount: "
            if min_amount > 0 and max_amount > 0:
                amount_filter += f"${min_amount:,.2f} - ${max_amount:,.2f}"
            elif min_amount > 0:
                amount_filter += f">= ${min_amount:,.2f}"
            else:
                amount_filter += f"<= ${max_amount:,.2f}"
            active_filters.append(amount_filter)
        if search_query:
            active_filters.append(f"🔍 Search: '{search_query}'")
        
        # Display active filters
        if active_filters:
            st.info("**Active Filters:** " + " | ".join(active_filters))
        
        # Display result count with summary statistics
        total_amount = df['amount'].sum()
        avg_amount = df['amount'].mean()
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("📊 Results Found", f"{len(df):,}")
        with col_stat2:
            st.metric("💵 Total Amount", f"${total_amount:,.2f}")
        with col_stat3:
            st.metric("📈 Average Amount", f"${avg_amount:,.2f}")
        with col_stat4:
            export_btn = st.button("📥 Export Results")
            if export_btn:
                # Convert to CSV for download
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Format for display
        df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d')
        df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
        
        # Add icon to type column
        df['type'] = df['type'].apply(lambda x: f"{get_type_icon(x)} {x}")
        
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
