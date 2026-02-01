"""
Reconciliation Page for CashFlow-Local

Provides bank account reconciliation workflow and variance analysis.

Author: Antigravity AI
License: MIT
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import logging

from src.database import db_manager
from src.reconciliation import ReconciliationEngine

logger = logging.getLogger(__name__)


def render_reconciliation_page():
    """Render the reconciliation page."""
    st.title("⚖️ Account Reconciliation")
    st.markdown("Reconcile your accounts to ensure your app data matches your bank statements.")
    
    # Initialize reconciliation engine
    reconciliation_engine = ReconciliationEngine(db_manager)
    
    # Check if accounts exist
    accounts = db_manager.get_accounts(active_only=True)
    if not accounts:
        st.warning("⚠️ No accounts found. Please add an account first in the 'Accounts' page.")
        return
    
    # Create tabs for different reconciliation features
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Reconcile Balance",
        "📊 Balance History",
        "🔄 Duplicate Detection",
        "📋 Reconciliation Report"
    ])
    
    with tab1:
        render_balance_reconciliation(accounts, reconciliation_engine)
    
    with tab2:
        render_balance_history(accounts)
    
    with tab3:
        render_duplicate_detection(accounts, reconciliation_engine)
    
    with tab4:
        render_reconciliation_report(accounts, reconciliation_engine)


def render_balance_reconciliation(accounts, reconciliation_engine):
    """Render balance reconciliation interface."""
    st.subheader("Balance Reconciliation Wizard")
    st.markdown("Compare your app balance with your actual bank statement.")
    
    # Step 1: Select account
    st.markdown("### Step 1: Select Account")
    selected_account_name = st.selectbox(
        "Choose an account to reconcile",
        options=[acc['name'] for acc in accounts],
        key="reconcile_account"
    )
    
    account = next((acc for acc in accounts if acc['name'] == selected_account_name), None)
    if not account:
        return
    
    # Step 2: Select statement date
    st.markdown("### Step 2: Enter Statement Details")
    col1, col2 = st.columns(2)
    
    with col1:
        statement_date = st.date_input(
            "Statement Date",
            value=datetime.now().date(),
            help="The date on your bank statement"
        )
    
    with col2:
        statement_balance = st.number_input(
            "Statement Balance",
            value=0.0,
            step=100.0,
            format="%.2f",
            help="The balance shown on your bank statement"
        )
    
    # Step 3: Calculate and compare
    if st.button("🔍 Analyze Balance", type="primary"):
        try:
            # Calculate app balance
            calculated_balance = db_manager.calculate_account_balance(
                account_id=account['id'],
                as_of_date=statement_date
            )
            
            # Analyze variance
            analysis = reconciliation_engine.analyze_variance(
                account_id=account['id'],
                statement_date=statement_date,
                statement_balance=statement_balance
            )
            
            # Save balance snapshot
            db_manager.save_balance_snapshot(
                account_id=account['id'],
                balance_date=statement_date,
                calculated_balance=calculated_balance,
                actual_balance=statement_balance
            )
            
            # Display results
            st.markdown("### 📊 Reconciliation Results")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "App Balance",
                    f"₹{calculated_balance:,.2f}",
                    help="Balance calculated from transactions"
                )
            
            with col2:
                st.metric(
                    "Bank Statement",
                    f"₹{statement_balance:,.2f}",
                    help="Balance from your bank statement"
                )
            
            with col3:
                variance = analysis['variance']
                variance_color = "off" if abs(variance) < 0.01 else "normal"
                st.metric(
                    "Variance",
                    f"₹{variance:,.2f}",
                    delta=f"{analysis['variance_percentage']:.2f}%",
                    delta_color=variance_color
                )
            
            # Status indicator
            if analysis['is_reconciled']:
                st.success("✅ **Reconciled!** Your balances match (difference < ₹0.01)")
            else:
                st.warning(f"⚠️ **Variance Detected**: ₹{variance:,.2f} difference found")
                
                # Show suggestions
                st.markdown("#### 💡 Suggestions")
                suggestions = reconciliation_engine.suggest_missing_transactions(
                    account_id=account['id'],
                    start_date=statement_date - timedelta(days=30),
                    end_date=statement_date,
                    expected_balance=statement_balance
                )
                
                for suggestion in suggestions:
                    st.markdown(f"- {suggestion}")
            
            # Show unreconciled transactions
            if analysis['unreconciled_count'] > 0:
                st.markdown("#### 📝 Unreconciled Transactions")
                st.info(f"Found {analysis['unreconciled_count']} unreconciled transaction(s)")
                
                unreconciled_df = pd.DataFrame(analysis['unreconciled_transactions'])
                if not unreconciled_df.empty:
                    display_df = unreconciled_df[[
                        'transaction_date', 'description', 'amount', 'type', 'category'
                    ]].copy()
                    display_df.columns = ['Date', 'Description', 'Amount', 'Type', 'Category']
                    display_df['Amount'] = display_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Bulk reconcile option
                    if st.button("✅ Mark All as Reconciled"):
                        txn_ids = unreconciled_df['id'].tolist()
                        db_manager.mark_transactions_reconciled(txn_ids, reconciled=True)
                        st.success(f"Marked {len(txn_ids)} transactions as reconciled!")
                        st.rerun()
        
        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
            st.error(f"❌ Reconciliation failed: {e}")


def render_balance_history(accounts):
    """Render balance history visualization."""
    st.subheader("Balance History Timeline")
    
    # Select account
    selected_account_name = st.selectbox(
        "Choose an account",
        options=[acc['name'] for acc in accounts],
        key="history_account"
    )
    
    account = next((acc for acc in accounts if acc['name'] == selected_account_name), None)
    if not account:
        return
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From Date",
            value=datetime.now().date() - timedelta(days=90)
        )
    with col2:
        end_date = st.date_input(
            "To Date",
            value=datetime.now().date()
        )
    
    try:
        # Get balance history
        history = db_manager.get_balance_history(
            account_id=account['id'],
            start_date=start_date,
            end_date=end_date
        )
        
        if not history:
            st.info("📭 No balance history found for this period.")
            st.markdown("💡 **Tip**: Perform a reconciliation to create balance snapshots.")
            return
        
        # Create DataFrame
        df = pd.DataFrame(history)
        df['balance_date'] = pd.to_datetime(df['balance_date'])
        df = df.sort_values('balance_date')
        
        # Create timeline chart
        fig = go.Figure()
        
        # Calculated balance line
        fig.add_trace(go.Scatter(
            x=df['balance_date'],
            y=df['calculated_balance'],
            mode='lines+markers',
            name='App Balance',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=8)
        ))
        
        # Actual balance line (if available)
        if 'actual_balance' in df.columns and df['actual_balance'].notna().any():
            fig.add_trace(go.Scatter(
                x=df['balance_date'],
                y=df['actual_balance'],
                mode='lines+markers',
                name='Bank Statement',
                line=dict(color='#2ca02c', width=2, dash='dash'),
                marker=dict(size=8, symbol='diamond')
            ))
        
        fig.update_layout(
            title=f"Balance Timeline - {selected_account_name}",
            xaxis_title="Date",
            yaxis_title="Balance (₹)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show variance details
        if 'variance' in df.columns and df['variance'].notna().any():
            st.markdown("### Variance Details")
            
            variance_df = df[df['variance'].notna()][
                ['balance_date', 'calculated_balance', 'actual_balance', 'variance', 'is_reconciled']
            ].copy()
            
            if not variance_df.empty:
                variance_df.columns = ['Date', 'App Balance', 'Bank Balance', 'Variance', 'Reconciled']
                variance_df['App Balance'] = variance_df['App Balance'].apply(lambda x: f"₹{x:,.2f}")
                variance_df['Bank Balance'] = variance_df['Bank Balance'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "-")
                variance_df['Variance'] = variance_df['Variance'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "-")
                variance_df['Reconciled'] = variance_df['Reconciled'].apply(lambda x: "✅" if x else "❌")
                
                st.dataframe(variance_df, use_container_width=True, hide_index=True)
    
    except Exception as e:
        logger.error(f"Error loading balance history: {e}")
        st.error(f"❌ Failed to load balance history: {e}")


def render_duplicate_detection(accounts, reconciliation_engine):
    """Render duplicate transaction detection."""
    st.subheader("Duplicate Transaction Detection")
    st.markdown("Find potential duplicate transactions in your account.")
    
    # Select account
    selected_account_name = st.selectbox(
        "Choose an account",
        options=[acc['name'] for acc in accounts],
        key="duplicate_account"
    )
    
    account = next((acc for acc in accounts if acc['name'] == selected_account_name), None)
    if not account:
        return
    
    # Detection parameters
    col1, col2 = st.columns(2)
    with col1:
        threshold_days = st.slider(
            "Date Threshold (days)",
            min_value=1,
            max_value=7,
            value=3,
            help="Consider transactions within this many days as potential duplicates"
        )
    
    with col2:
        amount_tolerance = st.number_input(
            "Amount Tolerance",
            min_value=0.0,
            max_value=10.0,
            value=0.01,
            step=0.01,
            help="Allow this much difference in amounts"
        )
    
    if st.button("🔍 Detect Duplicates", type="primary"):
        try:
            with st.spinner("Analyzing transactions..."):
                duplicates = reconciliation_engine.detect_duplicates(
                    account_id=account['id'],
                    threshold_days=threshold_days,
                    amount_tolerance=amount_tolerance
                )
            
            if not duplicates:
                st.success("✅ No duplicate transactions found!")
                return
            
            st.warning(f"⚠️ Found {len(duplicates)} potential duplicate pair(s)")
            
            # Display duplicates
            for i, dup in enumerate(duplicates, 1):
                with st.expander(f"Duplicate Pair #{i} - Similarity: {dup['similarity']*100:.1f}%"):
                    col1, col2, col3 = st.columns(3)
                    
                    txn1 = dup['transaction1']
                    txn2 = dup['transaction2']
                    
                    with col1:
                        st.markdown("**Transaction 1**")
                        st.write(f"Date: {txn1['transaction_date']}")
                        st.write(f"Description: {txn1['description']}")
                        st.write(f"Amount: ₹{txn1['amount']:,.2f}")
                        st.write(f"Type: {txn1['type']}")
                    
                    with col2:
                        st.markdown("**Transaction 2**")
                        st.write(f"Date: {txn2['transaction_date']}")
                        st.write(f"Description: {txn2['description']}")
                        st.write(f"Amount: ₹{txn2['amount']:,.2f}")
                        st.write(f"Type: {txn2['type']}")
                    
                    with col3:
                        st.markdown("**Analysis**")
                        st.write(f"Date Difference: {dup['date_diff']} days")
                        st.write(f"Amount Difference: ₹{dup['amount_diff']:.2f}")
                        st.write(f"Similarity: {dup['similarity']*100:.1f}%")
                        
                        # Action button
                        if st.button(f"🗑️ Delete Transaction 2", key=f"delete_{i}"):
                            st.info("⚠️ Deletion feature not implemented in this version. Please delete manually from Transactions page.")
        
        except Exception as e:
            logger.error(f"Duplicate detection error: {e}")
            st.error(f"❌ Duplicate detection failed: {e}")


def render_reconciliation_report(accounts, reconciliation_engine):
    """Render comprehensive reconciliation report."""
    st.subheader("Reconciliation Report")
    st.markdown("Generate a comprehensive report for a specific period.")
    
    # Select account
    selected_account_name = st.selectbox(
        "Choose an account",
        options=[acc['name'] for acc in accounts],
        key="report_account"
    )
    
    account = next((acc for acc in accounts if acc['name'] == selected_account_name), None)
    if not account:
        return
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From Date",
            value=datetime.now().date() - timedelta(days=30),
            key="report_start"
        )
    with col2:
        end_date = st.date_input(
            "To Date",
            value=datetime.now().date(),
            key="report_end"
        )
    
    if st.button("📋 Generate Report", type="primary"):
        try:
            with st.spinner("Generating report..."):
                report = reconciliation_engine.generate_reconciliation_report(
                    account_id=account['id'],
                    start_date=start_date,
                    end_date=end_date
                )
            
            # Display summary
            st.markdown("### 📊 Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            summary = report['summary']
            
            with col1:
                st.metric("Opening Balance", f"₹{summary['opening_balance']:,.2f}")
            with col2:
                st.metric("Closing Balance", f"₹{summary['closing_balance']:,.2f}")
            with col3:
                st.metric("Net Change", f"₹{summary['net_change']:,.2f}")
            with col4:
                reconciled_pct = summary['reconciliation_percentage']
                st.metric("Reconciled", f"{reconciled_pct:.1f}%")
            
            # Transaction breakdown
            st.markdown("### 📈 Transaction Breakdown")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Transactions", summary['total_transactions'])
            with col2:
                st.metric("✅ Reconciled", summary['reconciled_count'])
            with col3:
                st.metric("❌ Unreconciled", summary['unreconciled_count'])
            
            # Unreconciled transactions
            if summary['unreconciled_count'] > 0:
                st.markdown("### ⚠️ Unreconciled Transactions")
                
                unreconciled = pd.DataFrame(report['transactions']['unreconciled'])
                if not unreconciled.empty:
                    display_df = unreconciled[[
                        'transaction_date', 'description', 'amount', 'type', 'category'
                    ]].copy()
                    display_df.columns = ['Date', 'Description', 'Amount', 'Type', 'Category']
                    display_df['Amount'] = display_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Export option
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Report (CSV)",
                        data=csv,
                        file_name=f"reconciliation_report_{account['name']}_{start_date}_{end_date}.csv",
                        mime="text/csv"
                    )
        
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            st.error(f"❌ Failed to generate report: {e}")
