
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from src.database import db_manager

def render_dashboard_page(): # Renamed to match import in app.py
    render_stats_view()

def render_stats_view():
    """
    Render the Stats/Dashboard View (Realbyte style).
    """
    st.header("📊 Statistics")
    
    # 1. Month Selector (Reuse logic or make a shared component later)
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_date = st.date_input("Period", value=date.today(), key="stats_date")
        
    start_of_month = selected_date.replace(day=1)
    if selected_date.month == 12:
        end_of_month = date(selected_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(selected_date.year, selected_date.month + 1, 1) - timedelta(days=1)
        
    transactions = db_manager.get_transactions(
        start_date=start_of_month,
        end_date=end_of_month,
        limit=5000
    )
    
    if not transactions:
        st.info("No transactions found for this period.")
        return

    df = pd.DataFrame(transactions)
    
    # 2. Tabs for Income / Expense / Transfer (Realbyte logic)
    tab1, tab2 = st.tabs(["Expense", "Income"])
    
    with tab1:
        render_category_chart(df, "Expense", total_center=True)
        
    with tab2:
        render_category_chart(df, "Income", total_center=True)
        
    st.divider()
    
    # 3. Daily Trend
    st.subheader("Daily Trend")
    # Group by date and type
    if 'transaction_date' in df.columns:
        daily = df.groupby(['transaction_date', 'type'])['amount'].sum().reset_index()
        # Ensure date is standard format
        fig_trend = px.bar(
            daily, 
            x='transaction_date', 
            y='amount', 
            color='type',
            color_discrete_map={'Income': '#4CAF50', 'Expense': '#FF5252', 'Transfer': '#9E9E9E'},
            barmode='group',
            title="Daily Income vs Expense"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

def render_category_chart(df: pd.DataFrame, type_filter: str, total_center: bool = False):
    """
    Render Donut Chart for a specific type.
    """
    data = df[df['type'] == type_filter]
    
    if data.empty:
        st.caption(f"No {type_filter} records.")
        return
        
    total_amount = data['amount'].sum()
    
    # Group by category
    cat_summary = data.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)
    
    # Realbyte Style Donut
    fig = px.pie(
        cat_summary, 
        values='amount', 
        names='category',
        hole=0.6,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig.update_traces(textinfo='percent+label')
    
    if total_center:
        fig.update_layout(
            annotations=[dict(text=f"${total_amount:,.2f}", x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
    st.plotly_chart(fig, use_container_width=True)
    
    # List breakdown
    st.markdown("### Breakdown")
    for _, row in cat_summary.iterrows():
        pct = (row['amount'] / total_amount) * 100
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 5px; border-bottom: 1px solid #333;">
            <span>{row['category']}</span>
            <span>
                <span style="color: #888; margin-right: 10px;">{pct:.1f}%</span>
                <b>${row['amount']:,.2f}</b>
            </span>
        </div>
        """, unsafe_allow_html=True)
