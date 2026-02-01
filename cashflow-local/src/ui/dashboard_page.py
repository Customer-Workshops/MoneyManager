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

logger = logging.getLogger(__name__)


def get_kpis() -> Dict[str, Any]:
    """
    Calculate key performance indicators.
    
    Returns:
        Dictionary with KPI values
    """
    try:
        # Get current month date range
        today = datetime.now()
        start_of_month = today.replace(day=1)
        
        # Total balance (latest transaction balance calculation)
        balance_query = """
            SELECT 
                SUM(CASE WHEN type = 'Credit' THEN amount ELSE -amount END) as total_balance
            FROM transactions
        """
        balance_result = db_manager.execute_query(balance_query)
        total_balance = balance_result[0][0] if balance_result and balance_result[0][0] else 0
        
        # Monthly spend (current month debits)
        monthly_spend_query = """
            SELECT SUM(amount)
            FROM transactions
            WHERE type = 'Debit' 
            AND transaction_date >= ?
        """
        spend_result = db_manager.execute_query(monthly_spend_query, (start_of_month,))
        monthly_spend = spend_result[0][0] if spend_result and spend_result[0][0] else 0
        
        # Monthly income (current month credits)
        monthly_income_query = """
            SELECT SUM(amount)
            FROM transactions
            WHERE type = 'Credit' 
            AND transaction_date >= ?
        """
        income_result = db_manager.execute_query(monthly_income_query, (start_of_month,))
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
    """Render line chart showing income vs expenses over time."""
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
        
        # Create Plotly line chart
        fig = go.Figure()
        
        if 'Credit' in df_pivot.columns:
            fig.add_trace(go.Scatter(
                x=df_pivot['month'],
                y=df_pivot['Credit'],
                name='Income',
                mode='lines+markers',
                line=dict(color='#10b981', width=3),
                marker=dict(size=8)
            ))
        
        if 'Debit' in df_pivot.columns:
            fig.add_trace(go.Scatter(
                x=df_pivot['month'],
                y=df_pivot['Debit'],
                name='Expenses',
                mode='lines+markers',
                line=dict(color='#ef4444', width=3),
                marker=dict(size=8)
            ))
        
        fig.update_layout(
            title="Income vs Expenses Over Time",
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Failed to render income/expense chart: {e}")
        st.error("Failed to load income/expense chart")


def render_category_donut_chart():
    """Render donut chart showing spending by category."""
    try:
        query = """
            SELECT 
                category,
                SUM(amount) as total
            FROM transactions
            WHERE type = 'Debit'
            AND category != 'Uncategorized'
            GROUP BY category
            ORDER BY total DESC
            LIMIT 10
        """
        
        results = db_manager.execute_query(query)
        
        if not results:
            st.info("No categorized spending data available")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['category', 'total'])
        
        # Create donut chart
        fig = px.pie(
            df,
            values='total',
            names='category',
            title='Spending by Category',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Failed to render category chart: {e}")
        st.error("Failed to load category breakdown")


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


def render_dashboard_page():
    """
    Render the main dashboard page.
    
    Displays:
    - KPI metrics (Balance, Spend, Income, Savings Rate)
    - Line chart: Income vs Expenses
    - Donut chart: Spending by Category
    - Bar chart: Budget vs Actual
    """
    st.header("📊 Financial Dashboard")
    
    # KPIs
    kpis = get_kpis()
    render_kpi_cards(kpis)
    
    st.divider()
    
    # Charts in two columns
    col1, col2 = st.columns(2)
    
    with col1:
        render_income_expense_chart()
    
    with col2:
        render_category_donut_chart()
    
    st.divider()
    
    # Budget comparison (full width)
    render_budget_chart()
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Dashboard", type="primary"):
        st.rerun()
