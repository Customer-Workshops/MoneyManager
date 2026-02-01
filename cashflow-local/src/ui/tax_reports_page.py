"""
Tax Reports Page for CashFlow-Local Streamlit App

Allows users to tag transactions with Indian tax categories and generate tax reports.
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime, date
from typing import Optional
import io

from src.database import db_manager

logger = logging.getLogger(__name__)


def render_tax_reports_page():
    """
    Render the tax reports and management page.
    
    Features:
    - View tax categories and limits
    - Tag transactions with tax categories
    - View tax utilization summary
    - Generate tax reports
    - Export tax data to Excel
    """
    st.header("📋 Tax Reports & Management")
    st.markdown("""
    Track tax-deductible expenses for ITR filing. Tag your transactions with 
    relevant tax categories (80C, 80D, HRA, etc.) and generate reports.
    """)
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tax Summary", 
        "🏷️ Tag Transactions", 
        "📈 Category Details",
        "📥 Export Reports"
    ])
    
    # Tab 1: Tax Summary Dashboard
    with tab1:
        render_tax_summary()
    
    # Tab 2: Tag Transactions
    with tab2:
        render_transaction_tagging()
    
    # Tab 3: Category Details
    with tab3:
        render_category_details()
    
    # Tab 4: Export Reports
    with tab4:
        render_export_reports()


def render_tax_summary():
    """Render tax summary dashboard with utilization metrics."""
    st.subheader("Tax Deduction Summary")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Default to current financial year (April to March)
        current_date = datetime.now()
        if current_date.month >= 4:
            default_start = date(current_date.year, 4, 1)
            default_end = date(current_date.year + 1, 3, 31)
        else:
            default_start = date(current_date.year - 1, 4, 1)
            default_end = date(current_date.year, 3, 31)
        
        start_date = st.date_input(
            "Financial Year Start",
            value=default_start,
            key="tax_summary_start"
        )
    
    with col2:
        end_date = st.date_input(
            "Financial Year End",
            value=default_end,
            key="tax_summary_end"
        )
    
    with col3:
        st.write("")
        st.write("")
        refresh = st.button("🔄 Refresh", type="primary")
    
    try:
        # Get tax summary
        tax_summary = db_manager.get_tax_summary(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time())
        )
        
        if not tax_summary:
            st.info("No tax data available. Start tagging transactions in the '🏷️ Tag Transactions' tab!")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(tax_summary)
        
        # Display KPIs
        st.markdown("### 💰 Tax Savings Overview")
        
        # Calculate total deductions
        total_deductions = df['total_amount'].sum()
        
        # Estimate tax savings (assuming 30% tax bracket)
        estimated_savings = total_deductions * 0.30
        
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        
        with kpi_col1:
            st.metric(
                "Total Deductions",
                f"₹{total_deductions:,.2f}",
                help="Total tax-deductible expenses"
            )
        
        with kpi_col2:
            st.metric(
                "Estimated Tax Savings",
                f"₹{estimated_savings:,.2f}",
                help="Estimated tax savings at 30% tax bracket"
            )
        
        with kpi_col3:
            tagged_count = df['transaction_count'].sum()
            st.metric(
                "Tagged Transactions",
                f"{int(tagged_count)}",
                help="Number of transactions tagged for tax deductions"
            )
        
        st.divider()
        
        # Display category-wise summary
        st.markdown("### 📊 Category-wise Utilization")
        
        # Format the data for display
        display_df = df[['name', 'section', 'total_amount', 'annual_limit', 'utilization_percent', 'transaction_count']].copy()
        display_df.columns = ['Category', 'Section', 'Amount Used (₹)', 'Annual Limit (₹)', 'Utilization %', 'Transactions']
        
        # Add progress bars
        for idx, row in display_df.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{row['Category']}** ({row['Section']})")
            
            with col2:
                if pd.notna(row['Annual Limit (₹)']) and row['Annual Limit (₹)'] > 0:
                    utilization = row['Utilization %'] if pd.notna(row['Utilization %']) else 0
                    progress_color = "🟢" if utilization < 70 else "🟡" if utilization < 90 else "🔴"
                    st.progress(min(utilization / 100, 1.0))
                    st.caption(f"{progress_color} ₹{row['Amount Used (₹)']:,.2f} / ₹{row['Annual Limit (₹)']:,.2f}")
                else:
                    st.caption(f"₹{row['Amount Used (₹)']:,.2f} (No limit)")
            
            with col3:
                st.caption(f"{int(row['Transactions'])} txns")
        
    except Exception as e:
        logger.error(f"Failed to load tax summary: {e}")
        st.error(f"Failed to load tax summary: {str(e)}")


def render_transaction_tagging():
    """Render transaction tagging interface."""
    st.subheader("Tag Transactions for Tax Deductions")
    
    st.markdown("""
    Select transactions and assign tax categories to them. Transactions can have multiple tax tags.
    """)
    
    try:
        # Get all tax categories
        tax_categories = db_manager.get_all_tax_categories()
        category_options = {cat['name']: cat['id'] for cat in tax_categories}
        
        # Date range for filtering transactions
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "From Date",
                value=date.today().replace(month=1, day=1),
                key="tag_start"
            )
        
        with col2:
            end_date = st.date_input(
                "To Date",
                value=date.today(),
                key="tag_end"
            )
        
        # Get transactions
        transactions = db_manager.get_transactions(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            limit=500
        )
        
        if not transactions:
            st.info("No transactions found for the selected date range.")
            return
        
        # Display transactions with tagging interface
        st.markdown("### Recent Transactions")
        
        # Filter by category (optional)
        filter_category = st.selectbox(
            "Filter by Category (optional)",
            options=["All"] + sorted(list(set(t['category'] for t in transactions))),
            key="filter_category"
        )
        
        if filter_category != "All":
            transactions = [t for t in transactions if t['category'] == filter_category]
        
        # Paginate transactions
        items_per_page = 20
        total_pages = (len(transactions) + items_per_page - 1) // items_per_page
        
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=max(1, total_pages),
            value=1,
            key="tag_page"
        )
        
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(transactions))
        page_transactions = transactions[start_idx:end_idx]
        
        st.caption(f"Showing {start_idx + 1}-{end_idx} of {len(transactions)} transactions")
        
        # Display each transaction with tag options
        for txn in page_transactions:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.markdown(f"**{txn['description'][:40]}...**" if len(txn['description']) > 40 else f"**{txn['description']}**")
                    st.caption(f"{txn['transaction_date']} • {txn['category']}")
                
                with col2:
                    amount_color = "red" if txn['type'] == 'Debit' else "green"
                    st.markdown(f":{amount_color}[₹{abs(txn['amount']):,.2f}]")
                
                with col3:
                    # Get existing tags
                    existing_tags = db_manager.get_transaction_tax_tags(txn['id'])
                    existing_tag_names = [tag['name'] for tag in existing_tags]
                    
                    # Multi-select for tax tags
                    selected_tags = st.multiselect(
                        "Tax Tags",
                        options=list(category_options.keys()),
                        default=existing_tag_names,
                        key=f"tags_{txn['id']}",
                        label_visibility="collapsed"
                    )
                
                with col4:
                    if st.button("💾 Save Tags", key=f"save_{txn['id']}", type="secondary"):
                        # Get selected category IDs
                        selected_ids = {category_options[name] for name in selected_tags}
                        existing_ids = {tag['id'] for tag in existing_tags}
                        
                        # Add new tags
                        for cat_id in selected_ids - existing_ids:
                            db_manager.add_tax_tag(txn['id'], cat_id)
                        
                        # Remove deselected tags
                        for cat_id in existing_ids - selected_ids:
                            db_manager.remove_tax_tag(txn['id'], cat_id)
                        
                        st.success("Tags updated!", icon="✅")
                        st.rerun()
                
                st.divider()
    
    except Exception as e:
        logger.error(f"Failed to load transaction tagging: {e}")
        st.error(f"Failed to load transaction tagging: {str(e)}")


def render_category_details():
    """Render detailed view of transactions by tax category."""
    st.subheader("Tax Category Details")
    
    try:
        # Get all tax categories
        tax_categories = db_manager.get_all_tax_categories()
        
        if not tax_categories:
            st.info("No tax categories available.")
            return
        
        # Category selector
        category_options = {f"{cat['name']} ({cat['section']})": cat for cat in tax_categories}
        selected_category_name = st.selectbox(
            "Select Tax Category",
            options=list(category_options.keys())
        )
        
        selected_category = category_options[selected_category_name]
        
        # Display category info
        st.markdown(f"### {selected_category['name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Section:** {selected_category['section']}")
            st.markdown(f"**Description:** {selected_category['description']}")
        
        with col2:
            if selected_category['annual_limit']:
                st.markdown(f"**Annual Limit:** ₹{selected_category['annual_limit']:,.2f}")
            else:
                st.markdown("**Annual Limit:** No limit")
        
        st.divider()
        
        # Date range selector
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "From Date",
                value=date.today().replace(month=1, day=1),
                key="detail_start"
            )
        
        with col2:
            end_date = st.date_input(
                "To Date",
                value=date.today(),
                key="detail_end"
            )
        
        # Get transactions for this category
        transactions = db_manager.get_transactions_by_tax_category(
            tax_category_id=selected_category['id'],
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time())
        )
        
        if not transactions:
            st.info("No transactions found for this tax category in the selected date range.")
            return
        
        # Display summary metrics
        total_amount = sum(abs(t['amount']) for t in transactions)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Amount", f"₹{total_amount:,.2f}")
        
        with col2:
            st.metric("Transaction Count", len(transactions))
        
        with col3:
            if selected_category['annual_limit']:
                utilization = (total_amount / selected_category['annual_limit']) * 100
                st.metric("Utilization", f"{utilization:.1f}%")
            else:
                st.metric("Utilization", "N/A")
        
        st.divider()
        
        # Display transactions table
        st.markdown("### Transactions")
        
        df = pd.DataFrame(transactions)
        display_df = df[['transaction_date', 'description', 'amount', 'category']].copy()
        display_df.columns = ['Date', 'Description', 'Amount (₹)', 'Category']
        display_df['Amount (₹)'] = display_df['Amount (₹)'].apply(lambda x: f"₹{abs(x):,.2f}")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    
    except Exception as e:
        logger.error(f"Failed to load category details: {e}")
        st.error(f"Failed to load category details: {str(e)}")


def render_export_reports():
    """Render export and report generation interface."""
    st.subheader("Export Tax Reports")
    
    st.markdown("""
    Generate and download tax reports in various formats for ITR filing or sharing with your CA.
    """)
    
    try:
        # Date range selector
        col1, col2 = st.columns(2)
        
        with col1:
            # Default to current financial year
            current_date = datetime.now()
            if current_date.month >= 4:
                default_start = date(current_date.year, 4, 1)
                default_end = date(current_date.year + 1, 3, 31)
            else:
                default_start = date(current_date.year - 1, 4, 1)
                default_end = date(current_date.year, 3, 31)
            
            start_date = st.date_input(
                "Financial Year Start",
                value=default_start,
                key="export_start"
            )
        
        with col2:
            end_date = st.date_input(
                "Financial Year End",
                value=default_end,
                key="export_end"
            )
        
        st.divider()
        
        # Export options
        st.markdown("### 📥 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Export Summary to Excel", type="primary"):
                excel_data = generate_excel_report(start_date, end_date)
                if excel_data:
                    st.download_button(
                        label="⬇️ Download Excel Report",
                        data=excel_data,
                        file_name=f"tax_report_{start_date}_{end_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with col2:
            if st.button("📄 Generate Detailed Report", type="secondary"):
                st.info("PDF report generation coming soon!")
        
        st.divider()
        
        # Preview section
        st.markdown("### 👁️ Report Preview")
        
        tax_summary = db_manager.get_tax_summary(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time())
        )
        
        if not tax_summary:
            st.info("No tax data available for the selected period.")
            return
        
        df = pd.DataFrame(tax_summary)
        
        # Display preview table
        display_df = df[['section', 'name', 'total_amount', 'annual_limit', 'transaction_count']].copy()
        display_df.columns = ['Section', 'Category', 'Amount (₹)', 'Limit (₹)', 'Transactions']
        display_df['Amount (₹)'] = display_df['Amount (₹)'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "₹0.00")
        display_df['Limit (₹)'] = display_df['Limit (₹)'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "No Limit")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    
    except Exception as e:
        logger.error(f"Failed to load export reports: {e}")
        st.error(f"Failed to load export reports: {str(e)}")


def generate_excel_report(start_date: date, end_date: date) -> Optional[bytes]:
    """
    Generate Excel report with tax summary and detailed transactions.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
    
    Returns:
        Excel file as bytes, or None if generation fails
    """
    try:
        # Create Excel writer
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Summary sheet
            tax_summary = db_manager.get_tax_summary(
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time())
            )
            
            if tax_summary:
                summary_df = pd.DataFrame(tax_summary)
                summary_df = summary_df[['section', 'name', 'description', 'total_amount', 'annual_limit', 'utilization_percent', 'transaction_count']]
                summary_df.columns = ['Section', 'Category', 'Description', 'Amount', 'Annual Limit', 'Utilization %', 'Transactions']
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed transactions by category
            tax_categories = db_manager.get_all_tax_categories()
            
            for category in tax_categories:
                transactions = db_manager.get_transactions_by_tax_category(
                    tax_category_id=category['id'],
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time())
                )
                
                if transactions:
                    txn_df = pd.DataFrame(transactions)
                    txn_df = txn_df[['transaction_date', 'description', 'amount', 'category']]
                    txn_df.columns = ['Date', 'Description', 'Amount', 'Category']
                    
                    # Sanitize sheet name (Excel has limitations)
                    sheet_name = category['section'][:31]  # Excel sheet name limit
                    txn_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return output.getvalue()
    
    except Exception as e:
        logger.error(f"Failed to generate Excel report: {e}")
        st.error(f"Failed to generate Excel report: {str(e)}")
        return None
