"""
Reports Page for CashFlow-Local Streamlit App

Provides UI for generating and exporting financial reports in PDF, Excel, CSV, and JSON formats.
"""

import streamlit as st
from datetime import datetime, timedelta
import logging

from src.reports import report_generator
from src.categorization import category_engine

logger = logging.getLogger(__name__)


def render_reports_page():
    """
    Render the reports and data export page.
    
    Features:
    - Report type selection
    - Date range and category filters
    - Export to PDF, Excel, CSV, JSON
    """
    st.header("📄 Reports & Data Export")
    
    st.markdown("""
    Generate professional reports for tax filing, expense claims, or financial planning.
    Export your data in multiple formats for further analysis.
    """)
    
    # Report type selection
    st.subheader("Select Report Type")
    
    report_type = st.selectbox(
        "Report Type",
        options=[
            "Monthly Statement",
            "Tax Report",
            "Category Report",
            "Transaction Listing"
        ],
        help="Choose the type of report you want to generate"
    )
    
    st.markdown("---")
    
    # Common filters
    st.subheader("Filters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Date range filter
        if report_type == "Tax Report":
            # Default to current tax year
            current_year = datetime.now().year
            start_date = st.date_input(
                "Start Date",
                value=datetime(current_year, 1, 1).date(),
                help="Tax year start date"
            )
            end_date = st.date_input(
                "End Date",
                value=datetime(current_year, 12, 31).date(),
                help="Tax year end date"
            )
        else:
            # Default to last 30 days
            end_date = datetime.now().date()
            start_date = (end_date - timedelta(days=30))
            
            start_date = st.date_input(
                "Start Date",
                value=start_date,
                help="Report start date"
            )
            end_date = st.date_input(
                "End Date",
                value=end_date,
                help="Report end date"
            )
    
    with col2:
        # Category filter (not for Tax Report)
        category = None
        transaction_type = None
        
        if report_type == "Category Report":
            all_categories = category_engine.get_all_categories()
            category = st.selectbox(
                "Category",
                options=all_categories,
                help="Select category to report on"
            )
        elif report_type != "Tax Report":
            all_categories = category_engine.get_all_categories()
            category = st.selectbox(
                "Category (Optional)",
                options=["All"] + all_categories,
                help="Filter by category"
            )
            if category == "All":
                category = None
        
        # Transaction type filter (only for Transaction Listing)
        if report_type == "Transaction Listing":
            transaction_type = st.selectbox(
                "Transaction Type (Optional)",
                options=["All", "Credit", "Debit"],
                help="Filter by transaction type"
            )
            if transaction_type == "All":
                transaction_type = None
    
    st.markdown("---")
    
    # Export format selection
    st.subheader("Export Format")
    
    export_format = st.radio(
        "Choose export format",
        options=["PDF", "Excel", "CSV", "JSON"],
        horizontal=True,
        help="Select the format for your report"
    )
    
    # Format descriptions
    format_descriptions = {
        "PDF": "📄 Professional formatted report with summary and visualizations",
        "Excel": "📊 Spreadsheet with multiple sheets (transactions, summary, category breakdown)",
        "CSV": "📋 Simple comma-separated values file for data analysis",
        "JSON": "💾 Structured data format for backup and data portability"
    }
    
    st.info(format_descriptions[export_format])
    
    st.markdown("---")
    
    # Generate button
    if st.button("📥 Generate Report", type="primary", use_container_width=True):
        try:
            with st.spinner(f"Generating {report_type} in {export_format} format..."):
                # Convert dates to datetime
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                # Generate report based on type and format
                if export_format == "PDF":
                    if report_type == "Monthly Statement":
                        buffer = report_generator.generate_monthly_statement_pdf(
                            start_datetime, end_datetime, category
                        )
                        filename = f"monthly_statement_{start_date}_{end_date}.pdf"
                    elif report_type == "Tax Report":
                        buffer = report_generator.generate_tax_report_pdf(
                            start_datetime, end_datetime
                        )
                        filename = f"tax_report_{start_date.year}.pdf"
                    elif report_type == "Category Report":
                        buffer = report_generator.generate_category_report_pdf(
                            start_datetime, end_datetime, category
                        )
                        filename = f"category_report_{category}_{start_date}_{end_date}.pdf"
                    else:  # Transaction Listing
                        buffer = report_generator.generate_transaction_listing_pdf(
                            start_datetime, end_datetime, category, transaction_type
                        )
                        filename = f"transaction_listing_{start_date}_{end_date}.pdf"
                    
                    mime_type = "application/pdf"
                
                elif export_format == "Excel":
                    buffer = report_generator.export_to_excel(
                        start_datetime, end_datetime, category, transaction_type
                    )
                    filename = f"transactions_{start_date}_{end_date}.xlsx"
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
                elif export_format == "CSV":
                    buffer = report_generator.export_to_csv(
                        start_datetime, end_datetime, category, transaction_type
                    )
                    filename = f"transactions_{start_date}_{end_date}.csv"
                    mime_type = "text/csv"
                
                else:  # JSON
                    buffer = report_generator.export_to_json(
                        start_datetime, end_datetime, category, transaction_type
                    )
                    filename = f"transactions_{start_date}_{end_date}.json"
                    mime_type = "application/json"
                
                # Download button
                st.success(f"✅ {report_type} generated successfully!")
                
                st.download_button(
                    label=f"⬇️ Download {export_format}",
                    data=buffer,
                    file_name=filename,
                    mime=mime_type,
                    use_container_width=True
                )
        
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            st.error(f"Failed to generate report: {str(e)}")
            st.error("Please check if you have transactions in the selected date range.")
    
    # Help section
    st.markdown("---")
    
    with st.expander("ℹ️ Report Type Descriptions"):
        st.markdown("""
        ### Monthly Statement
        A comprehensive overview of your finances for a given period:
        - Income vs Expenses summary
        - Category breakdown
        - Top transactions
        
        ### Tax Report
        Focused on tax-deductible expenses:
        - Filtered by tax-relevant categories
        - Organized by deduction type
        - Year-end summary
        - Detailed transaction listing
        
        ### Category Report
        Deep dive into a specific spending category:
        - Total spent and average transaction
        - All transactions in the category
        - Helpful for budget analysis
        
        ### Transaction Listing
        Complete list of transactions with your filters:
        - All transaction details
        - Flexible filtering options
        - Best for comprehensive exports
        """)
    
    with st.expander("💡 Tips"):
        st.markdown("""
        - **PDF Reports**: Best for sharing with accountants or for record-keeping
        - **Excel**: Great for further analysis, creating charts, or pivot tables
        - **CSV**: Simple format compatible with all spreadsheet applications
        - **JSON**: Ideal for backing up data or importing into other systems
        
        **Tax Reports**: Automatically filter for common deductible categories like:
        - Business Expenses
        - Home Office
        - Medical
        - Charitable Donations
        - Education
        - Professional Development
        """)
