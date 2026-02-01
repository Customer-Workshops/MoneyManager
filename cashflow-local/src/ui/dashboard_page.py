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
from src.bills import bill_manager

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
    col1, col2, col3, col4, col5 = st.columns(5)
    
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
    
    with col5:
        render_bills_summary_card()


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


def render_goals_overview():
    """
    Render goals overview section with top 3 goals and progress tracking.
    """
    st.subheader("🎯 Financial Goals Overview")
    
    try:
        goals = get_top_goals(limit=3)
        
        if not goals:
            st.info("📋 No financial goals set yet. Visit the Goals page to create your first goal!")
            if st.button("➕ Create Your First Goal"):
                st.switch_page("pages/goals_page.py")  # Note: This won't work with our navigation, just showing intent
            return
        
        # Display each goal in columns
        cols = st.columns(min(len(goals), 3))
        
        for idx, goal in enumerate(goals):
            with cols[idx]:
                # Goal card with icon
                goal_icon = get_goal_icon(goal['goal_type'])
                st.markdown(f"#### {goal_icon} {goal['name']}")
                
                # Progress bar
                progress = goal['progress_percent'] / 100
                st.progress(progress)
                
                # Progress percentage
                status_color = "🟢" if goal['is_on_track'] else "🔴"
                st.markdown(f"{status_color} **{goal['progress_percent']:.1f}%** Complete")
                
                # Key metrics
                st.metric(
                    "Saved / Target",
                    f"₹{goal['current_amount']:,.0f}",
                    delta=f"₹{goal['remaining_amount']:,.0f} to go"
                )
                
                st.metric(
                    "Monthly Required",
                    f"₹{goal['required_monthly']:,.0f}"
                )
                
                # Target date
                target_date = goal['target_date']
                if isinstance(target_date, str):
                    from datetime import datetime
                    target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
                
                days_text = f"{goal['days_remaining']} days" if goal['days_remaining'] > 0 else "Overdue!"
                st.caption(f"Target: {target_date.strftime('%b %d, %Y')} ({days_text})")
        
        # Add link to goals page
        st.markdown("---")
        st.markdown("📊 [View All Goals & Add Contributions](#) - Visit the **🎯 Goals** page")
        
        # Savings recommendations
        if goals:
            total_monthly_required = sum(g['required_monthly'] for g in goals)
            st.info(f"💡 **Savings Tip:** To reach all your top goals, allocate ₹{total_monthly_required:,.0f} per month")
            
            # Check for off-track goals
            off_track_goals = [g for g in goals if not g['is_on_track']]
            if off_track_goals:
                st.warning(f"⚠️ {len(off_track_goals)} goal(s) are behind schedule. Consider increasing your savings rate!")
    
    except Exception as e:
        logger.error(f"Failed to render goals overview: {e}")
        st.error("Failed to load goals overview")


def render_dashboard_page():
    """
    Render the main dashboard page.
    
    Displays:
    - KPI metrics (Balance, Spend, Income, Savings Rate, Bills)
    - Overdue bills alert
    - Line chart: Income vs Expenses (Trend Analysis)
    - Donut chart: Spending by Category
    - Bar chart: Top Merchants/Payees
    - Budget Progress Bars with color-coded alerts
    - Goals Overview with progress tracking
    """
    st.header("📊 Financial Dashboard")
    
    # Overdue bills alert (if any)
    render_overdue_bills_alert()
    
    # KPIs
    kpis = get_kpis()
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
    
    st.divider()
    
    # Goals Overview
    render_goals_overview()
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Dashboard", type="primary"):
        st.rerun()
