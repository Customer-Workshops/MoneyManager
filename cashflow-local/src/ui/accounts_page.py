"""
Accounts Page for CashFlow-Local Streamlit App

Displays and manages financial accounts (bank accounts, credit cards, wallets).
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any

from src.database import db_manager

logger = logging.getLogger(__name__)

# Account type options with icons
ACCOUNT_TYPES = {
    'Savings Account': '🏦',
    'Checking Account': '💳',
    'Credit Card': '💳',
    'Digital Wallet': '📱',
    'Cash': '💵'
}


def render_accounts_page():
    """
    Render the accounts management page.
    
    Features:
    - View all accounts
    - Add new account
    - Edit existing account
    - Delete account
    - View account balances
    """
    st.header("🏦 Accounts")
    st.markdown("""
    Manage your financial accounts. Track multiple bank accounts, credit cards, and wallets.
    """)
    
    # Add new account section
    with st.expander("➕ Add New Account", expanded=False):
        render_add_account_form()
    
    st.divider()
    
    # Display existing accounts
    st.subheader("Your Accounts")
    render_accounts_list()


def render_add_account_form():
    """Render form to add a new account."""
    with st.form("add_account_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            account_name = st.text_input(
                "Account Name*",
                placeholder="e.g., Chase Checking, AMEX Card",
                help="Give your account a recognizable name"
            )
            
            account_type = st.selectbox(
                "Account Type*",
                options=list(ACCOUNT_TYPES.keys()),
                help="Select the type of account"
            )
        
        with col2:
            initial_balance = st.number_input(
                "Initial Balance",
                value=0.0,
                step=100.0,
                format="%.2f",
                help="Current balance of this account"
            )
            
            currency = st.selectbox(
                "Currency",
                options=['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD'],
                help="Account currency"
            )
        
        submitted = st.form_submit_button("Add Account", type="primary", use_container_width=True)
        
        if submitted:
            if not account_name:
                st.error("❌ Account name is required")
            else:
                try:
                    account_id = db_manager.create_account(
                        name=account_name,
                        account_type=account_type,
                        balance=initial_balance,
                        currency=currency
                    )
                    st.success(f"✅ Account '{account_name}' created successfully!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Failed to create account: {e}")
                    st.error(f"❌ Failed to create account: {str(e)}")


def render_accounts_list():
    """Display list of existing accounts with edit/delete options."""
    try:
        accounts = db_manager.get_all_accounts()
        
        if not accounts:
            st.info("No accounts found. Add your first account above!")
            return
        
        # Create DataFrame for display
        df = pd.DataFrame(accounts)
        
        # Calculate actual balances from transactions
        for idx, account in enumerate(accounts):
            calculated_balance = db_manager.get_account_balance(account['id'])
            df.loc[idx, 'calculated_balance'] = calculated_balance
        
        # Display summary card
        total_balance = df['calculated_balance'].sum()
        st.metric(
            label="💰 Total Net Worth",
            value=f"${total_balance:,.2f}",
            help="Sum of all account balances based on transactions"
        )
        
        st.divider()
        
        # Display each account
        for idx, account in enumerate(accounts):
            render_account_card(account, df.loc[idx, 'calculated_balance'])
    
    except Exception as e:
        logger.error(f"Failed to load accounts: {e}")
        st.error(f"❌ Failed to load accounts: {str(e)}")


def render_account_card(account: Dict[str, Any], calculated_balance: float):
    """
    Render a single account card with edit/delete functionality.
    
    Args:
        account: Account dictionary
        calculated_balance: Balance calculated from transactions
    """
    account_id = account['id']
    
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        
        with col1:
            icon = ACCOUNT_TYPES.get(account['type'], '🏦')
            st.markdown(f"### {icon} {account['name']}")
            st.caption(f"**Type:** {account['type']}")
        
        with col2:
            st.metric(
                label="Set Balance",
                value=f"${account['balance']:,.2f}",
                help="Balance set in account settings"
            )
        
        with col3:
            balance_diff = calculated_balance - account['balance']
            st.metric(
                label="Actual Balance",
                value=f"${calculated_balance:,.2f}",
                delta=f"${balance_diff:,.2f}" if balance_diff != 0 else None,
                help="Balance calculated from transactions"
            )
        
        with col4:
            st.markdown("**Actions**")
            col_edit, col_delete = st.columns(2)
            
            with col_edit:
                if st.button("✏️", key=f"edit_{account_id}", help="Edit account"):
                    st.session_state[f'editing_{account_id}'] = True
                    st.rerun()
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{account_id}", help="Delete account"):
                    try:
                        db_manager.delete_account(account_id)
                        st.success(f"✅ Account '{account['name']}' deleted")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Failed to delete account: {e}")
                        st.error(f"❌ Failed to delete account: {str(e)}")
        
        # Show edit form if editing this account
        if st.session_state.get(f'editing_{account_id}', False):
            with st.form(f"edit_account_form_{account_id}"):
                st.markdown("#### Edit Account")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input("Account Name", value=account['name'])
                    new_type = st.selectbox(
                        "Account Type",
                        options=list(ACCOUNT_TYPES.keys()),
                        index=list(ACCOUNT_TYPES.keys()).index(account['type']) if account['type'] in ACCOUNT_TYPES else 0
                    )
                
                with col2:
                    new_balance = st.number_input(
                        "Balance",
                        value=float(account['balance']),
                        step=100.0,
                        format="%.2f"
                    )
                    new_currency = st.selectbox(
                        "Currency",
                        options=['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD'],
                        index=['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD'].index(account['currency']) if account['currency'] in ['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD'] else 0
                    )
                
                col_save, col_cancel = st.columns(2)
                
                with col_save:
                    save_button = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                
                with col_cancel:
                    cancel_button = st.form_submit_button("Cancel", use_container_width=True)
                
                if save_button:
                    try:
                        db_manager.update_account(
                            account_id=account_id,
                            name=new_name,
                            account_type=new_type,
                            balance=new_balance,
                            currency=new_currency
                        )
                        st.session_state[f'editing_{account_id}'] = False
                        st.success(f"✅ Account '{new_name}' updated successfully!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Failed to update account: {e}")
                        st.error(f"❌ Failed to update account: {str(e)}")
                
                if cancel_button:
                    st.session_state[f'editing_{account_id}'] = False
                    st.rerun()
        
        st.divider()
