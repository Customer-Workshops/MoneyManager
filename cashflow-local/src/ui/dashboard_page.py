"""
Dashboard Page for CashFlow-Local Streamlit App

Displays KPIs, visualizations, and budget tracking.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
from typing import Dict, Any

from src.database import db_manager
from src.ui.utils import get_type_icon

logger = logging.getLogger(__name__)


def get_kpis(account_id: int = None) -> Dict[str, Any]:
    """
    Calculate key performance indicators.
    
    Args:
        account_id: Optional account filter (None = All Accounts)
    
    Returns:
        Dictionary with KPI values
    """
    try:
        # Get current month date range
        today = datetime.now()
        start_of_month = today.replace(day=1)
        
        # Build WHERE clause for account filter
        account_filter = ""
        params_balance = []
        params_spend = [start_of_month]
        params_income = [start_of_month]
        
        if account_id is not None:
            account_filter = " AND account_id = ?"
            params_balance = [account_id]
            params_spend.append(account_id)
            params_income.append(account_id)
        
        # Total balance (latest transaction balance calculation)
        balance_query = f"""
            SELECT 
                SUM(CASE WHEN type = 'Credit' THEN amount ELSE -amount END) as total_balance
            FROM transactions
            WHERE 1=1 {account_filter}
        """
        balance_result = db_manager.execute_query(balance_query, tuple(params_balance) if params_balance else None)
        total_balance = balance_result[0][0] if balance_result and balance_result[0][0] else 0
        
        # Monthly spend (current month debits)
        monthly_spend_query = f"""
            SELECT SUM(amount)
            FROM transactions
            WHERE type = 'Debit' 
            AND transaction_date >= ? {account_filter}
        """
        spend_result = db_manager.execute_query(monthly_spend_query, tuple(params_spend))
        monthly_spend = spend_result[0][0] if spend_result and spend_result[0][0] else 0
        
        # Monthly income (current month credits)
        monthly_income_query = f"""
            SELECT SUM(amount)
            FROM transactions
            WHERE type = 'Credit' 
            AND transaction_date >= ? {account_filter}
        """
        income_result = db_manager.execute_query(monthly_income_query, tuple(params_income))
        monthly_income = income_result[0][0] if income_result and income_result[0][0] else 0
        
        # Savings rate
        savings_rate = 0
        if monthly_income > 0:
            savings_rate = ((monthly_income - monthly_spend) / monthly_income) * 100
        
        return {
            'total_balance': total_balance,
            'monthly_spend': monthly_spend,
            'monthly_income': monthly_income,
            'savings_rate': savings_rate
        }
    
    except Exception as e:
        logger.error(f"Failed to calculate KPIs: {e}")
        return {
            'total_balance': 0,
            'monthly_spend': 0,
            'monthly_income': 0,
            'savings_rate': 0
        }


def render_kpi_cards(kpis: Dict[str, Any]):
    """Render KPI metric cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Total Balance",
            f"${kpis['total_balance']:,.2f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "💸 Monthly Spend",
            f"${kpis['monthly_spend']:,.2f}",
            delta=None,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "💵 Monthly Income",
            f"${kpis['monthly_income']:,.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            "📈 Savings Rate",
            f"{kpis['savings_rate']:.1f}%",
            delta=None,
            delta_color="normal"
        )


def render_income_expense_chart():
    """Render interactive line chart showing income vs expenses over time with trend analysis."""
    try:
        query = """
            SELECT 
                DATE_TRUNC('month', transaction_date) as month,
                type,
                SUM(amount) as total
            FROM transactions
            GROUP BY month, type
            ORDER BY month
        """
        
        results = db_manager.execute_query(query)
        
        if not results:
            st.info("No data available for chart")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['month', 'type', 'total'])
        
        # Pivot for plotting
        df_pivot = df.pivot(index='month', columns='type', values='total').fillna(0)
        df_pivot = df_pivot.reset_index()
        
        # Create Plotly line chart with enhanced interactivity
        fig = go.Figure()
        
        if 'Credit' in df_pivot.columns:
            fig.add_trace(go.Scatter(
                x=df_pivot['month'],
                y=df_pivot['Credit'],
                name='💰 Income',
                mode='lines+markers',
                line=dict(color='#10b981', width=3),
                marker=dict(size=8),
                hovertemplate='<b>Income</b><br>Date: %{x}<br>Amount: $%{y:,.2f}<extra></extra>'
            ))
        
        if 'Debit' in df_pivot.columns:
            fig.add_trace(go.Scatter(
                x=df_pivot['month'],
                y=df_pivot['Debit'],
                name='💸 Expenses',
                mode='lines+markers',
                line=dict(color='#ef4444', width=3),
                marker=dict(size=8),
                hovertemplate='<b>Expenses</b><br>Date: %{x}<br>Amount: $%{y:,.2f}<extra></extra>'
            ))
        
        # Add net savings/deficit line if both exist
        if 'Credit' in df_pivot.columns and 'Debit' in df_pivot.columns:
            df_pivot['net'] = df_pivot['Credit'] - df_pivot['Debit']
            fig.add_trace(go.Scatter(
                x=df_pivot['month'],
                y=df_pivot['net'],
                name='📈 Net Savings',
                mode='lines+markers',
                line=dict(color='#3b82f6', width=2, dash='dash'),
                marker=dict(size=6),
                hovertemplate='<b>Net Savings</b><br>Date: %{x}<br>Amount: $%{y:,.2f}<extra></extra>'
            ))
        
        fig.update_layout(
            title="📈 Income vs Expenses Trend Analysis",
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            hovermode='x unified',
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Failed to render income/expense chart: {e}")
        st.error("Failed to load income/expense chart")


def render_category_donut_chart():
    """Render interactive donut chart showing spending by category with enhanced tooltips."""
    try:
        query = """
            SELECT 
                category,
                SUM(amount) as total,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE type = 'Debit'
            AND category != 'Uncategorized'
            AND transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY category
            ORDER BY total DESC
            LIMIT 10
        """
        
        results = db_manager.execute_query(query)
        
        if not results:
            st.info("No categorized spending data available")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['category', 'total', 'transaction_count'])
        
        # Calculate percentages
        df['percentage'] = (df['total'] / df['total'].sum() * 100).round(1)
        
        # Create interactive donut chart with enhanced tooltips
        fig = px.pie(
            df,
            values='total',
            names='category',
            title='📊 Spending by Category (Current Month)',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        # Update traces with custom hover template
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>' +
                         'Amount: $%{value:,.2f}<br>' +
                         'Percentage: %{percent}<br>' +
                         '<extra></extra>'
        )
        
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Failed to render category chart: {e}")
        st.error("Failed to load category breakdown")


def render_budget_progress_bars():
    """Render budget tracking dashboard with progress bars and color-coded alerts."""
    try:
        query = """
            SELECT 
                b.category as category,
                COALESCE(SUM(t.amount), 0) as actual,
                b.monthly_limit as budget
            FROM budgets b
            LEFT JOIN (
                SELECT category, SUM(amount) as amount
                FROM transactions
                WHERE type = 'Debit'
                AND DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY category
            ) t ON b.category = t.category
            GROUP BY b.category, b.monthly_limit
        """
        
        results = db_manager.execute_query(query)
        
        if not results:
            st.info("No budgets configured. Go to the Budgets page to set up category budgets.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['category', 'actual', 'budget'])
        
        st.subheader("💵 Budget Tracking Dashboard")
        
        # Display each budget as a progress bar with color coding
        for _, row in df.iterrows():
            percentage = (row['actual'] / row['budget'] * 100) if row['budget'] > 0 else 0
            
            # Color coding: 🟢 < 70%, 🟡 70-90%, 🔴 > 90%
            if percentage < 70:
                color_indicator = "🟢"
                bar_color = "#10b981"  # Green
            elif percentage < 90:
                color_indicator = "🟡"
                bar_color = "#f59e0b"  # Yellow/Orange
            else:
                color_indicator = "🔴"
                bar_color = "#ef4444"  # Red
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{color_indicator} {row['category']}**")
                st.progress(min(percentage / 100, 1.0))
                st.caption(f"${row['actual']:,.2f} of ${row['budget']:,.2f} ({percentage:.1f}%)")
            
            with col2:
                remaining = row['budget'] - row['actual']
                if remaining >= 0:
                    st.metric("Remaining", f"${remaining:,.2f}")
                else:
                    st.metric("Over Budget", f"${abs(remaining):,.2f}", delta_color="inverse")
    
    except Exception as e:
        logger.error(f"Failed to render budget progress bars: {e}")
        st.error("Failed to load budget tracking")


def render_budget_chart():
    """Render bar chart comparing budget vs actual spending."""
    try:
        query = """
            SELECT 
                b.category as category,
                COALESCE(SUM(t.amount), 0) as actual,
                b.monthly_limit as budget
            FROM budgets b
            LEFT JOIN (
                SELECT category, SUM(amount) as amount
                FROM transactions
                WHERE type = 'Debit'
                AND DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY category
            ) t ON b.category = t.category
            GROUP BY b.category, b.monthly_limit
        """
        
        results = db_manager.execute_query(query)
        
        if not results:
            st.info("No budgets configured. Go to the Budgets page to set up category budgets.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['category', 'actual', 'budget'])
        
        # Determine colors (red if over budget)
        df['color'] = df.apply(
            lambda row: '#ef4444' if row['actual'] > row['budget'] else '#3b82f6',
            axis=1
        )
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['category'],
            y=df['budget'],
            name='Budget',
            marker_color='#9ca3af'
        ))
        
        fig.add_trace(go.Bar(
            x=df['category'],
            y=df['actual'],
            name='Actual',
            marker_color=df['color']
        ))
        
        fig.update_layout(
            title="Budget vs Actual Spending",
            xaxis_title="Category",
            yaxis_title="Amount ($)",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Failed to render budget chart: {e}")
        st.error("Failed to load budget comparison")


def render_top_merchants_chart():
    """Render bar chart showing top merchants/payees by total transaction amount."""
    try:
        query = """
            SELECT 
                description,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count,
                type
            FROM transactions
            WHERE type = 'Debit'
            AND transaction_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 months'
            GROUP BY description, type
            ORDER BY total_amount DESC
            LIMIT 10
        """
        
        results = db_manager.execute_query(query)
        
        if not results:
            st.info("No transaction data available for merchant analysis")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['description', 'total_amount', 'transaction_count', 'type'])
        
        # Truncate long descriptions
        df['short_desc'] = df['description'].apply(lambda x: x[:30] + '...' if len(x) > 30 else x)
        
        # Create bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['total_amount'],
            y=df['short_desc'],
            orientation='h',
            marker_color='#8b5cf6',
            text=df['total_amount'].apply(lambda x: f'${x:,.2f}'),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Total: $%{x:,.2f}<br>Transactions: %{customdata}<extra></extra>',
            customdata=df['transaction_count']
        ))
        
        fig.update_layout(
            title="🏪 Top Merchants/Payees (Last 3 Months)",
            xaxis_title="Total Amount ($)",
            yaxis_title="Merchant/Payee",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Failed to render top merchants chart: {e}")
        st.error("Failed to load merchant analysis")


def render_dashboard_page():
    """
    Render the main dashboard page.
    
    Displays:
    - Account selector
    - KPI metrics (Balance, Spend, Income, Savings Rate)
    - Line chart: Income vs Expenses (Trend Analysis)
    - Donut chart: Spending by Category
    - Bar chart: Top Merchants/Payees
    - Budget Progress Bars with color-coded alerts
    """
    st.header("📊 Financial Dashboard")
    
    # Account filter selector
    accounts = db_manager.get_all_accounts()
    
    if not accounts:
        st.warning("⚠️ No accounts found. Please create an account in the 🏦 Accounts page first.")
        return
    
    # Create account dropdown
    account_options = {"All Accounts": None}
    account_options.update({f"{acc['name']} ({acc['type']})": acc['id'] for acc in accounts})
    
    selected_account_name = st.selectbox(
        "View",
        options=list(account_options.keys()),
        help="Select an account to view its transactions, or 'All Accounts' for consolidated view"
    )
    selected_account_id = account_options[selected_account_name]
    
    st.divider()
    
    # KPIs
    kpis = get_kpis(selected_account_id)
    render_kpi_cards(kpis)
    
    st.divider()
    
    # Charts row 1: Trend and Category breakdown
    st.subheader("📈 Spending Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        render_income_expense_chart()
    
    with col2:
        render_category_donut_chart()
    
    st.divider()
    
    # Charts row 2: Top Merchants and Budget Tracking
    col1, col2 = st.columns(2)
    
    with col1:
        render_top_merchants_chart()
    
    with col2:
        render_budget_progress_bars()
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Dashboard", type="primary"):
        st.rerun()
