"""
Accounts Page for CashFlow-Local Streamlit App

Allows users to manage bank accounts, credit cards, and wallets.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import logging

from src.database import db_manager
from src.ui.utils import get_type_icon

logger = logging.getLogger(__name__)


def render_accounts_list(accounts: List[Dict[str, Any]]):
    """Render list of accounts as summary cards."""
    if not accounts:
        st.info("No accounts found. Create your first account using the sidebar form!")
        return

    st.subheader("Your Accounts")
    
    # Group accounts by type
    accounts_by_type = {}
    for acc in accounts:
        acc_type = acc['type']
        if acc_type not in accounts_by_type:
            accounts_by_type[acc_type] = []
        accounts_by_type[acc_type].append(acc)
    
    # Display accounts grouped by type
    for acc_type, type_accounts in accounts_by_type.items():
        st.markdown(f"### {get_type_icon(acc_type)} {acc_type}")
        
        cols = st.columns(3)
        for i, account in enumerate(type_accounts):
            with cols[i % 3]:
                with st.container():
                    # Card styling
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #e0e0e0;
                        border-radius: 10px;
                        padding: 15px;
                        background-color: white;
                        margin-bottom: 10px;
                    ">
                        <h4 style="margin: 0 0 10px 0;">{account['name']}</h4>
                        <div style="color: #666; font-size: 0.9em;">
                            {account['currency']} • {'Active' if account['is_active'] else 'Inactive'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Compute balance (placeholder until real balance calculation is efficient)
                    # balance = db_manager.calculate_account_balance(account['id'])
                    # st.metric("Balance", f"${balance:,.2f}")


def render_add_account_form():
    """Render form to add a new account."""
    with st.expander("➕ Add New Account", expanded=False):
        with st.form("add_account_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Account Name", placeholder="e.g., Chase Checking")
                acc_type = st.selectbox(
                    "Account Type",
                    options=["Checking", "Savings", "Credit Card", "Wallet", "Investment", "Loan"]
                )
            
            with col2:
                currency = st.selectbox(
                    "Currency",
                    options=["USD", "EUR", "GBP", "INR", "CAD", "AUD"],
                    index=3  # Default to INR based on context
                )
                initial_balance = st.number_input(
                    "Initial Balance",
                    value=0.0,
                    step=0.01,
                    help="Starting balance for this account"
                )
            
            submitted = st.form_submit_button("Create Account", type="primary")
            
            if submitted:
                if not name:
                    st.error("Please enter an account name")
                    return
                
                try:
                    # Insert account
                    query = """
                        INSERT INTO accounts (name, type, currency, is_active)
                        VALUES (?, ?, ?, ?)
                        RETURNING id
                    """
                    
                    with db_manager.get_connection() as conn:
                        result = conn.execute(query, [name, acc_type, currency, True]).fetchone()
                        
                        if result:
                            # If initial balance > 0, create an opening balance transaction
                            # (Logic placeholder as before)
                            pass
                                
                            st.success(f"Account '{name}' created successfully!")
                            st.rerun()
                            
                except Exception as e:
                    logger.error(f"Failed to create account: {e}")
                    st.error(f"Failed to create account: {str(e)}")


def render_accounts_page():
    """Render the main accounts management page."""
    st.header("🏦 Accounts Management")
    
    # Render add account form in sidebar
    render_add_account_form()
    
    # Get all accounts
    try:
        accounts = db_manager.get_all_accounts()
        render_accounts_list(accounts)
        
    except Exception as e:
        logger.error(f"Failed to load accounts: {e}")
        st.error("Failed to load accounts list")
