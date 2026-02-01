"""
Bills Page for CashFlow-Local Streamlit App

Allows users to manage bill reminders and payment alerts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging

from src.bills import bill_manager, BillManager

logger = logging.getLogger(__name__)


def render_bills_page():
    """
    Render the bills management page.
    
    Features:
    - View all bills
    - Add new bills
    - Mark bills as paid
    - View upcoming and overdue bills
    - Payment history
    """
    st.header("🔔 Bill Reminders & Payment Alerts")
    st.markdown("""
    Manage your recurring bills and get reminded before due dates.
    Never miss a payment again!
    """)
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 All Bills",
        "⏰ Upcoming & Overdue",
        "➕ Add New Bill",
        "📜 Payment History"
    ])
    
    # Tab 1: All Bills
    with tab1:
        render_all_bills()
    
    # Tab 2: Upcoming & Overdue Bills
    with tab2:
        render_upcoming_overdue_bills()
    
    # Tab 3: Add New Bill
    with tab3:
        render_add_bill_form()
    
    # Tab 4: Payment History
    with tab4:
        render_payment_history()


def render_all_bills():
    """Render all bills in a table."""
    st.subheader("All Bills")
    
    try:
        bills = bill_manager.get_all_bills()
        
        if not bills:
            st.info("No bills found. Add your first bill in the 'Add New Bill' tab!")
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(bills)
        
        # Format dates and amounts
        df['due_date'] = pd.to_datetime(df['due_date']).dt.strftime('%Y-%m-%d')
        df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
        
        # Add status emoji
        status_emoji = {
            'pending': '⏳',
            'paid': '✅',
            'overdue': '🔴'
        }
        df['status_display'] = df['status'].apply(lambda x: f"{status_emoji.get(x, '')} {x.title()}")
        
        # Select and reorder columns for display
        display_columns = ['name', 'bill_type', 'amount', 'due_date', 'recurrence', 
                          'reminder_days', 'status_display']
        df_display = df[display_columns].copy()
        df_display.columns = ['Bill Name', 'Type', 'Amount', 'Due Date', 
                             'Recurrence', 'Reminder (days)', 'Status']
        
        # Display editable table
        st.dataframe(
            df_display,
            hide_index=True,
            use_container_width=True
        )
        
        # Actions section
        st.divider()
        st.subheader("Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Mark bill as paid
            bill_names = [f"{b['name']} (${b['amount']:.2f} - {b['due_date']})" 
                         for b in bills if b['status'] != 'paid']
            
            if bill_names:
                selected_bill = st.selectbox(
                    "Select bill to mark as paid",
                    options=range(len(bill_names)),
                    format_func=lambda i: bill_names[i]
                )
                
                if st.button("✅ Mark as Paid", type="primary"):
                    # Find the corresponding bill ID
                    pending_bills = [b for b in bills if b['status'] != 'paid']
                    bill_id = pending_bills[selected_bill]['id']
                    
                    if bill_manager.mark_bill_paid(bill_id):
                        st.success(f"Bill marked as paid!")
                        st.rerun()
                    else:
                        st.error("Failed to mark bill as paid")
            else:
                st.info("No pending bills to pay")
        
        with col2:
            # Delete bill
            bill_names_all = [f"{b['name']} ({b['bill_type']})" for b in bills]
            
            selected_bill_delete = st.selectbox(
                "Select bill to delete",
                options=range(len(bill_names_all)),
                format_func=lambda i: bill_names_all[i],
                key="delete_select"
            )
            
            if st.button("🗑️ Delete Bill", type="secondary"):
                bill_id = bills[selected_bill_delete]['id']
                
                if bill_manager.delete_bill(bill_id):
                    st.success("Bill deleted!")
                    st.rerun()
                else:
                    st.error("Failed to delete bill")
        
        with col3:
            st.metric(
                "Total Bills",
                len(bills),
                delta=None
            )
            
            total_pending = sum(b['amount'] for b in bills if b['status'] == 'pending')
            st.metric(
                "Pending Amount",
                f"${total_pending:,.2f}",
                delta=None
            )
    
    except Exception as e:
        logger.error(f"Failed to render all bills: {e}")
        st.error(f"Failed to load bills: {str(e)}")


def render_upcoming_overdue_bills():
    """Render upcoming and overdue bills."""
    st.subheader("Upcoming Bills")
    
    try:
        # Get upcoming bills (next 30 days)
        upcoming = bill_manager.get_upcoming_bills(days_ahead=30)
        
        if upcoming:
            df_upcoming = pd.DataFrame(upcoming)
            # Calculate days_until_due before formatting due_date
            df_upcoming['days_until_due'] = (
                pd.to_datetime(df_upcoming['due_date']) - pd.Timestamp(datetime.now())
            ).dt.days
            
            # Now format the dates and amounts
            df_upcoming['due_date'] = pd.to_datetime(df_upcoming['due_date']).dt.strftime('%Y-%m-%d')
            df_upcoming['amount'] = df_upcoming['amount'].apply(lambda x: f"${x:,.2f}")
            
            # Add urgency indicator
            df_upcoming['urgency'] = df_upcoming['days_until_due'].apply(
                lambda x: '🔴 Urgent' if x <= 3 else '🟡 Soon' if x <= 7 else '🟢 Upcoming'
            )
            
            display_cols = ['name', 'bill_type', 'amount', 'due_date', 'days_until_due', 'urgency']
            df_display = df_upcoming[display_cols].copy()
            df_display.columns = ['Bill Name', 'Type', 'Amount', 'Due Date', 'Days Until Due', 'Urgency']
            
            st.dataframe(
                df_display,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No upcoming bills in the next 30 days")
        
        st.divider()
        
        # Overdue bills
        st.subheader("⚠️ Overdue Bills")
        
        overdue = bill_manager.get_overdue_bills()
        
        if overdue:
            df_overdue = pd.DataFrame(overdue)
            # Calculate days_overdue before formatting due_date
            df_overdue['days_overdue'] = (
                pd.Timestamp(datetime.now()) - pd.to_datetime(df_overdue['due_date'])
            ).dt.days
            
            # Now format the dates and amounts
            df_overdue['due_date'] = pd.to_datetime(df_overdue['due_date']).dt.strftime('%Y-%m-%d')
            df_overdue['amount'] = df_overdue['amount'].apply(lambda x: f"${x:,.2f}")
            
            display_cols = ['name', 'bill_type', 'amount', 'due_date', 'days_overdue']
            df_display = df_overdue[display_cols].copy()
            df_display.columns = ['Bill Name', 'Type', 'Amount', 'Due Date', 'Days Overdue']
            
            st.error(f"You have {len(overdue)} overdue bill(s)!")
            st.dataframe(
                df_display,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("✅ No overdue bills!")
        
        # Bills needing reminder
        st.divider()
        st.subheader("🔔 Bills Needing Attention")
        
        reminder_bills = bill_manager.get_bills_needing_reminder()
        
        if reminder_bills:
            for bill in reminder_bills:
                days_left = (bill['due_date'] - datetime.now().date()).days
                st.warning(
                    f"**{bill['name']}** ({bill['bill_type']}) - "
                    f"${bill['amount']:,.2f} - Due in {days_left} day(s) "
                    f"({bill['due_date'].strftime('%Y-%m-%d')})"
                )
        else:
            st.info("No bills need immediate attention")
    
    except Exception as e:
        logger.error(f"Failed to render upcoming/overdue bills: {e}")
        st.error(f"Failed to load bills: {str(e)}")


def render_add_bill_form():
    """Render form to add a new bill."""
    st.subheader("Add New Bill")
    
    with st.form("add_bill_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            bill_name = st.text_input(
                "Bill Name *",
                placeholder="e.g., Monthly Rent, Electricity Bill",
                help="Enter a descriptive name for this bill"
            )
            
            bill_type = st.selectbox(
                "Bill Type *",
                options=BillManager.BILL_TYPES,
                help="Select the type of bill"
            )
            
            amount = st.number_input(
                "Amount ($) *",
                min_value=0.0,
                value=50.0,
                step=10.0,
                format="%.2f",
                help="Enter the bill amount"
            )
            
            recurrence = st.selectbox(
                "Recurrence *",
                options=BillManager.RECURRENCE_TYPES,
                index=1,  # Default to Monthly
                help="How often does this bill recur?"
            )
        
        with col2:
            due_date = st.date_input(
                "Due Date *",
                value=datetime.now().date() + timedelta(days=7),
                min_value=datetime.now().date(),
                help="When is this bill due?"
            )
            
            reminder_days = st.number_input(
                "Remind me (days before) *",
                min_value=1,
                max_value=30,
                value=3,
                step=1,
                help="How many days before due date should you be reminded?"
            )
            
            notes = st.text_area(
                "Notes (optional)",
                placeholder="Additional notes about this bill...",
                help="Any additional information"
            )
        
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submit = st.form_submit_button("➕ Add Bill", type="primary", use_container_width=True)
        
        with col2:
            cancel = st.form_submit_button("Cancel", type="secondary", use_container_width=True)
        
        if submit:
            # Validate inputs
            if not bill_name or not bill_type:
                st.error("Please fill in all required fields (marked with *)")
            else:
                # Add the bill
                success = bill_manager.add_bill(
                    name=bill_name,
                    bill_type=bill_type,
                    amount=amount,
                    due_date=datetime.combine(due_date, datetime.min.time()),
                    recurrence=recurrence,
                    reminder_days=reminder_days,
                    notes=notes
                )
                
                if success:
                    st.success(f"✅ Bill '{bill_name}' added successfully!")
                    st.balloons()
                    # Wait a moment before rerun
                    st.rerun()
                else:
                    st.error("Failed to add bill. Please try again.")
        
        if cancel:
            st.info("Operation cancelled")


def render_payment_history():
    """Render payment history."""
    st.subheader("Payment History")
    
    try:
        history = bill_manager.get_payment_history(limit=50)
        
        if not history:
            st.info("No payment history yet. Paid bills will appear here.")
            return
        
        df = pd.DataFrame(history)
        
        # Calculate on-time payment rate BEFORE formatting dates
        on_time = sum(1 for h in history 
                     if h['last_paid_date'] and h['due_date'] 
                     and pd.to_datetime(h['last_paid_date']) <= pd.to_datetime(h['due_date']))
        on_time_rate = (on_time / len(history) * 100) if history else 0
        
        # Format dates and amounts for display
        df['due_date'] = pd.to_datetime(df['due_date']).dt.strftime('%Y-%m-%d')
        df['last_paid_date'] = pd.to_datetime(df['last_paid_date']).dt.strftime('%Y-%m-%d')
        df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
        
        # Select columns for display
        display_cols = ['name', 'bill_type', 'amount', 'due_date', 'last_paid_date', 'recurrence']
        df_display = df[display_cols].copy()
        df_display.columns = ['Bill Name', 'Type', 'Amount', 'Original Due Date', 
                             'Paid On', 'Recurrence']
        
        st.dataframe(
            df_display,
            hide_index=True,
            use_container_width=True
        )
        
        # Summary metrics
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Paid Bills",
                len(history)
            )
        
        with col2:
            total_paid = sum(float(h['amount']) for h in history)
            st.metric(
                "Total Amount Paid",
                f"${total_paid:,.2f}"
            )
        
        with col3:
            # Use pre-calculated on-time payment rate
            st.metric(
                "On-Time Payment Rate",
                f"{on_time_rate:.1f}%"
            )
    
    except Exception as e:
        logger.error(f"Failed to render payment history: {e}")
        st.error(f"Failed to load payment history: {str(e)}")
