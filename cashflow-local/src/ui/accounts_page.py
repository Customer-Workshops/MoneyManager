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


def render_accounts_page():
    """Render the main accounts management page."""
    st.header("🏦 Assets & Accounts")
    
    tab1, tab2, tab3 = st.tabs(["Overview", "Transfer", "Manage"])
    
    with tab1:
        render_accounts_list(db_manager.get_all_accounts())
        
    with tab2:
        render_transfer_form()
        
    with tab3:
        render_add_account_form()

def render_transfer_form():
    """Render form to transfer money between accounts."""
    st.subheader("💸 Transfer Money")
    
    accounts = db_manager.get_all_accounts()
    if len(accounts) < 2:
        st.info("You need at least 2 accounts to make a transfer.")
        return

    # Map name->id
    acc_map = {f"{a['name']} ({a['currency']})": a['id'] for a in accounts}
    
    with st.form("transfer_form"):
        col1, col2 = st.columns(2)
        with col1:
            from_acc_name = st.selectbox("From Account", options=list(acc_map.keys()))
        with col2:
            to_acc_name = st.selectbox("To Account", options=list(acc_map.keys()))
            
        amount = st.number_input("Amount", min_value=0.01, step=0.01)
        date_tx = st.date_input("Date", value=pd.to_datetime("today"))
        note = st.text_input("Note", placeholder="e.g. Credit Card Payment")
        
        submitted = st.form_submit_button("Submit Transfer", type="primary")
        
        if submitted:
            if from_acc_name == to_acc_name:
                st.error("Source and Destination accounts must be different.")
                return
            
            from_id = acc_map[from_acc_name]
            to_id = acc_map[to_acc_name]
            
            try:
                # 1. Get/Create "Transfer" category
                cat_id = db_manager.get_category_id("Transfer", "Expense") # Use generic Transfer cat
                
                # 2. Prepare Transactions (Double Entry for Transfer)
                # Tx 1: Withdrawal from Source
                tx_out = {
                    'transaction_date': date_tx,
                    'amount': amount,
                    'type': 'Expense', # or 'Transfer' if we strictly follow schema types
                    'category_id': cat_id,
                    'account_id': from_id,
                    'description': f"Transfer to {to_acc_name.split(' (')[0]}",
                    'note': note,
                    'hash_id': f"TRF-{from_id}-{to_id}-{amount}-{date_tx}-OUT", # Simple unique hash
                    'reconciled': False
                }
                
                # Tx 2: Deposit to Dest
                tx_in = {
                    'transaction_date': date_tx,
                    'amount': amount,
                    'type': 'Income',
                    'category_id': cat_id,
                    'account_id': to_id,
                    'description': f"Transfer from {from_acc_name.split(' (')[0]}",
                    'note': note,
                    'hash_id': f"TRF-{from_id}-{to_id}-{amount}-{date_tx}-IN",
                    'reconciled': False
                }
                
                # Insert
                db_manager.execute_insert('transactions', [tx_out, tx_in])
                st.success("Transfer successful!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Transfer failed: {e}")

def render_accounts_list(accounts: List[Dict[str, Any]]):
    """Render list of accounts as summary cards."""
    if not accounts:
        st.info("No accounts found. Create your first account in the 'Manage' tab!")
        return

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
                # Calculate Balance
                balance = db_manager.calculate_account_balance(account['id'])
                # Card Styling
                st.markdown(f"""
                <div style="
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    background-color: white;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                ">
                    <h4 style="margin: 0; color: #333;">{account['name']}</h4>
                    <p style="margin: 5px 0; font-size: 1.5em; font-weight: bold; color: {'#4CAF50' if balance >= 0 else '#FF5252'};">
                        {account.get('currency', '$')} {balance:,.2f}
                    </p>
                    <div style="color: #888; font-size: 0.8em;">
                        {acc_type} • {'Active' if account['is_active'] else 'Inactive'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

def render_add_account_form():
    """Render form to add a new account."""
    st.subheader("Manage Accounts")
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
                index=3  # Default to INR
            )
            initial_balance = st.number_input(
                "Initial Balance",
                value=0.0,
                step=0.01,
                help="Starting balance for this account"
            )
            opening_date = st.date_input("Opening Date", value=pd.to_datetime("today"))
        
        submitted = st.form_submit_button("Create Account", type="primary")
        
        if submitted:
            if not name:
                st.error("Please enter an account name")
                return
            
            try:
                # Insert account
                query = """
                    INSERT INTO accounts (name, type, currency, is_active, opening_balance, opening_balance_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    RETURNING id
                """
                
                with db_manager.get_connection() as conn:
                    conn.execute(query, [name, acc_type, currency, True, initial_balance, opening_date])
                    st.success(f"Account '{name}' created successfully!")
                    st.rerun()
                        
            except Exception as e:
                logger.error(f"Failed to create account: {e}")
                st.error(f"Failed to create account: {str(e)}")
