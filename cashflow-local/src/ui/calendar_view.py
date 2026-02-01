
import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, date, timedelta
import pandas as pd
from typing import Dict, Any, List

from src.database import db_manager
from src.ui.utils import get_type_icon

def render_calendar_view():
    """
    Render the main Calendar View (Realbyte style).
    """
    st.header("📅 Monthly Overview")
    
    # 1. Controls (Month Selector)
    col1, col2 = st.columns([1, 3])
    with col1:
        # Simple Month Picker (Defaults to current month)
        # Ideally this would be dynamic, but for V1 let's pick a date to center the calendar
        selected_date = st.date_input("Jump to Month", value=date.today())
    
    # 2. Fetch Data for the selected month
    # Logic: Get transactions for the whole month
    start_of_month = selected_date.replace(day=1)
    # End of month
    if selected_date.month == 12:
        end_of_month = date(selected_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(selected_date.year, selected_date.month + 1, 1) - timedelta(days=1)
        
    transactions = db_manager.get_transactions(
        start_date=start_of_month,
        end_date=end_of_month,
        limit=5000 # Allow many transactions
    )
    
    # 3. Monthly Summary
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'Income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'Expense')
    balance = total_income - total_expense
    
    # Header Metrics
    st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-around;">
        <div style="text-align: center;">
            <p style="margin:0; font-size: 0.9em; color: #888;">Income</p>
            <p style="margin:0; font-size: 1.2em; color: #4CAF50;">+${total_income:,.2f}</p>
        </div>
        <div style="text-align: center;">
            <p style="margin:0; font-size: 0.9em; color: #888;">Expenses</p>
            <p style="margin:0; font-size: 1.2em; color: #FF5252;">-${total_expense:,.2f}</p>
        </div>
        <div style="text-align: center;">
            <p style="margin:0; font-size: 0.9em; color: #888;">Total</p>
            <p style="margin:0; font-size: 1.2em; color: {'#4CAF50' if balance >= 0 else '#FF5252'};">${balance:,.2f}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 4. Prepare Calendar Events
    # We want to show Daily Totals on the calendar.
    # Group by date
    daily_stats = {}
    for t in transactions:
        d = t['transaction_date'] # Check format, might be date obj or string if from dict
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
            
        d_str = d.isoformat()
        if d_str not in daily_stats:
            daily_stats[d_str] = {'income': 0.0, 'expense': 0.0}
        
        if t['type'] == 'Income':
            daily_stats[d_str]['income'] += t['amount']
        elif t['type'] == 'Expense':
            daily_stats[d_str]['expense'] += t['amount']
            
    events = []
    for d_str, stats in daily_stats.items():
        if stats['income'] > 0:
            events.append({
                "title": f"+{int(stats['income'])}",
                "start": d_str,
                "backgroundColor": "transparent",
                "borderColor": "transparent",
                "textColor": "#4CAF50", # Green
                "classNames": ["income-event"]
            })
        if stats['expense'] > 0:
            events.append({
                "title": f"-{int(stats['expense'])}",
                "start": d_str,
                "backgroundColor": "transparent",
                "borderColor": "transparent",
                "textColor": "#FF5252", # Red
                "classNames": ["expense-event"]
            })

    # Calendar Config
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth"
        },
        "initialDate": selected_date.isoformat(),
        "contentHeight": "auto",
        "selectable": True,
    }
    
    # 5. Render Calendar
    cal_state = calendar(events=events, options=calendar_options, key="monthly_calendar")
    
    # 6. Interaction: Show details for clicked date
    if cal_state.get('dateClick'):
        clicked_date = cal_state['dateClick']['dateStr']
        st.subheader(f"Details for {clicked_date}")
        
        # Filter transactions for this date
        day_txns = [
            t for t in transactions 
            if (t['transaction_date'].isoformat() if isinstance(t['transaction_date'], date) else t['transaction_date']) == clicked_date
        ]
        
        if day_txns:
            for t in day_txns:
                icon = t.get('category_icon', 'receipt')
                color = t.get('category_color', '#888')
                with st.container():
                    c1, c2, c3 = st.columns([1, 4, 2])
                    with c1:
                        st.markdown(f"<div style='text-align: center; color: {color};'><span class='material-icons'>{icon}</span></div>", unsafe_allow_html=True)
                    with c2:
                        st.write(f"**{t['category']}**")
                        st.caption(t['description'])
                        if t.get('note'):
                            st.caption(f"📝 {t['note']}")
                    with c3:
                        amt_color = "#4CAF50" if t['type'] == 'Income' else "#FF5252"
                        sign = "+" if t['type'] == 'Income' else "-"
                        st.markdown(f"<p style='text-align: right; color: {amt_color}; font-weight: bold;'>{sign}${t['amount']:,.2f}</p>", unsafe_allow_html=True)
                    st.divider()
        else:
            st.info("No transactions on this date.")
