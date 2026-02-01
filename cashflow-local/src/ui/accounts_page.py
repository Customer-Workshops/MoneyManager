"""
Accounts Management Page for CashFlow-Local

Allows users to create, edit, and manage bank accounts with opening balances.

Author: Antigravity AI
License: MIT
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging

from src.database import db_manager

logger = logging.getLogger(__name__)


def render_accounts_page():
    """Render the accounts management page."""
    st.title("🏦 Accounts")
    st.markdown("Manage your bank accounts and set opening balances.")
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["📋 View Accounts", "➕ Add Account"])
    
    with tab1:
        render_accounts_list()
    
    with tab2:
        render_add_account_form()


def render_accounts_list():
    """Display list of all accounts."""
    st.subheader("Your Accounts")
    
    try:
        accounts = db_manager.get_accounts(active_only=False)
        
        if not accounts:
            st.info("📭 No accounts found. Add your first account using the 'Add Account' tab.")
            return
        
        # Display accounts in a table
        df = pd.DataFrame(accounts)
        
        # Format the display
        display_df = df[[
            'name', 'account_type', 'account_number', 
            'opening_balance', 'opening_balance_date', 'currency', 'is_active'
        ]].copy()
        
        display_df.columns = [
            'Account Name', 'Type', 'Account Number',
            'Opening Balance', 'Opening Date', 'Currency', 'Active'
        ]
        
        # Format currency
        display_df['Opening Balance'] = display_df['Opening Balance'].apply(
            lambda x: f"₹{x:,.2f}" if pd.notna(x) else "₹0.00"
        )
        
        # Format dates
        display_df['Opening Date'] = pd.to_datetime(display_df['Opening Date']).dt.strftime('%Y-%m-%d')
        
        # Display with conditional formatting
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Show account details and actions
        st.markdown("---")
        st.subheader("Account Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_account = st.selectbox(
                "Select an account to view details",
                options=[acc['name'] for acc in accounts],
                key="account_selector"
            )
        
        with col2:
            if st.button("🔄 Calculate Current Balance", key="calc_balance"):
                # Find the selected account
                account = next((acc for acc in accounts if acc['name'] == selected_account), None)
                if account:
                    try:
                        current_balance = db_manager.calculate_account_balance(account['id'])
                        st.success(f"💰 Current Balance: ₹{current_balance:,.2f}")
                    except Exception as e:
                        st.error(f"Error calculating balance: {e}")
        
        # Display selected account details
        if selected_account:
            account = next((acc for acc in accounts if acc['name'] == selected_account), None)
            if account:
                with st.expander(f"📊 Details for {selected_account}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Account Type", account['account_type'])
                        st.metric("Currency", account['currency'])
                    
                    with col2:
                        opening_bal = account['opening_balance'] or 0
                        st.metric("Opening Balance", f"₹{opening_bal:,.2f}")
                        if account['opening_balance_date']:
                            st.metric("Opening Date", str(account['opening_balance_date']))
                    
                    with col3:
                        status = "✅ Active" if account['is_active'] else "❌ Inactive"
                        st.metric("Status", status)
                        
                        current_balance = db_manager.calculate_account_balance(account['id'])
                        st.metric("Current Balance", f"₹{current_balance:,.2f}")
    
    except Exception as e:
        logger.error(f"Error loading accounts: {e}")
        st.error(f"Failed to load accounts: {e}")


def render_add_account_form():
    """Render form to add a new account."""
    st.subheader("Add New Account")
    
    with st.form("add_account_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            account_name = st.text_input(
                "Account Name *",
                placeholder="e.g., HDFC Savings",
                help="A unique name for this account"
            )
            
            account_type = st.selectbox(
                "Account Type *",
                options=["Checking", "Savings", "Credit Card", "Investment", "Other"],
                index=1
            )
            
            opening_balance = st.number_input(
                "Opening Balance *",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
                help="The balance at the opening date"
            )
        
        with col2:
            account_number = st.text_input(
                "Account Number (Optional)",
                placeholder="Last 4 digits recommended",
                help="For identification purposes only"
            )
            
            currency = st.selectbox(
                "Currency *",
                options=["INR", "USD", "EUR", "GBP", "JPY"],
                index=0
            )
            
            opening_date = st.date_input(
                "Opening Balance Date *",
                value=datetime.now().date(),
                help="The date from which the opening balance is valid"
            )
        
        is_active = st.checkbox("Active Account", value=True)
        
        submit_button = st.form_submit_button("➕ Add Account")
        
        if submit_button:
            # Validate inputs
            if not account_name:
                st.error("❌ Please provide an account name.")
                return
            
            try:
                # Check if account name already exists
                existing_accounts = db_manager.get_accounts(active_only=False)
                if any(acc['name'] == account_name for acc in existing_accounts):
                    st.error(f"❌ Account '{account_name}' already exists. Please use a different name.")
                    return
                
                # Insert new account
                account_data = {
                    'name': account_name,
                    'account_number': account_number or None,
                    'account_type': account_type,
                    'opening_balance': opening_balance,
                    'opening_balance_date': opening_date,
                    'currency': currency,
                    'is_active': is_active
                }
                
                db_manager.execute_insert('accounts', [account_data])
                
                st.success(f"✅ Account '{account_name}' added successfully!")
                st.info("💡 Tip: Go to the 'View Accounts' tab to see your new account.")
                
                # Clear form by rerunning
                st.rerun()
            
            except Exception as e:
                logger.error(f"Error adding account: {e}")
                st.error(f"❌ Failed to add account: {e}")
