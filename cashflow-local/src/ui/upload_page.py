"""
Upload Page for CashFlow-Local Streamlit App

Handles file upload (CSV/PDF), parsing, deduplication, and insertion.
"""

import streamlit as st
import tempfile
import os
from io import BytesIO
import logging

from src.parsers import create_parser, compute_file_hash
from src.deduplication import insert_transactions
from src.categorization import category_engine
from src.database import db_manager

logger = logging.getLogger(__name__)


def render_upload_page():
    """
    Render the file upload page.
    
    Features:
    - Multi-file upload (CSV/PDF)
    - Drag-and-drop interface
    - Real-time processing status
    - Duplicate statistics
    """
    st.header("📤 Upload Bank Statements")
    st.markdown("""
    Upload your bank statements (CSV or PDF format) to automatically import transactions.
    
    **Supported Formats:**
    - CSV files with columns: Date, Description, Debit/Credit or Amount
    - PDF bank statements with transaction tables
    
    **Smart Features:**
    - ✅ Automatic duplicate detection (upload the same file multiple times safely)
    - 🤖 Auto-categorization based on your rules
    - 📊 Instant statistics and validation
    """)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose bank statement files",
        type=['csv', 'pdf'],
        accept_multiple_files=True,
        help="Select one or more CSV or PDF files containing your bank transactions"
    )
    
    if uploaded_files:
        st.divider()
        st.subheader("Processing Files")
        
        # Process each file
        total_inserted = 0
        total_duplicates = 0
        total_errors = 0
        
        for uploaded_file in uploaded_files:
            st.markdown(f"**📄 {uploaded_file.name}**")
            
            # Create progress indicators
            progress_bar = st.progress(0, text=f"Processing {uploaded_file.name}...")
            status_text = st.empty()
            
            try:
                # Step 1: Compute file hash
                progress_bar.progress(10, text="Computing file hash...")
                file_content = BytesIO(uploaded_file.read())
                file_hash = compute_file_hash(file_content)
                
                # Step 2: Save to temp file (needed for pdfplumber)
                progress_bar.progress(20, text="Saving temporary file...")
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=os.path.splitext(uploaded_file.name)[1]
                ) as tmp_file:
                    file_content.seek(0)
                    tmp_file.write(file_content.read())
                    tmp_path = tmp_file.name
                
                # Step 3: Parse file
                progress_bar.progress(40, text="Parsing transactions...")
                parser = create_parser(tmp_path)
                df = parser.parse()
                
                # Debug: Show what was parsed
                st.info(f"📋 Parsed {len(df)} transactions from file")
                if len(df) > 0 and len(df) < 10:
                    with st.expander("🔍 View Parsed Data"):
                        st.dataframe(df)
                
                # Step 4: Categorize
                progress_bar.progress(60, text="Categorizing transactions...")
                df = category_engine.categorize_dataframe(df)
                
                # Step 5: Insert with deduplication
                progress_bar.progress(80, text="Inserting into database...")
                stats = insert_transactions(df, file_hash, db_manager)
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                # Update totals
                total_inserted += stats['inserted']
                total_duplicates += stats['duplicates']
                total_errors += stats['errors']
                
                # Display results
                progress_bar.progress(100, text="Complete!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("✅ Inserted", stats['inserted'], delta=None)
                with col2:
                    st.metric("🔄 Duplicates", stats['duplicates'], delta=None)
                with col3:
                    st.metric("❌ Errors", stats['errors'], delta=None)
                
                if stats['inserted'] > 0:
                    st.success(f"Successfully imported {stats['inserted']} new transactions!")
                elif stats['duplicates'] > 0:
                    st.info(f"All {stats['duplicates']} transactions already exist (duplicates skipped)")
                
            except Exception as e:
                logger.error(f"Failed to process {uploaded_file.name}: {e}")
                progress_bar.empty()
                st.error(f"❌ Failed to process file: {str(e)}")
                total_errors += 1
            
            st.divider()
        
        # Summary
        if len(uploaded_files) > 1:
            st.subheader("📊 Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Inserted", total_inserted)
            with col2:
                st.metric("Total Duplicates", total_duplicates)
            with col3:
                st.metric("Total Errors", total_errors)
    
    else:
        # Show placeholder
        st.info("👆 Upload files to get started")
        
        # Show sample data format
        with st.expander("📋 Show Sample CSV Format"):
            st.markdown("""
            ```csv
            Date,Description,Debit,Credit,Balance
            2026-01-15,STARBUCKS #1234,5.50,,1245.50
            2026-01-16,Salary Deposit,,3000.00,4245.50
            2026-01-17,AMAZON PURCHASE,125.99,,4119.51
            ```
            
            **Supported Column Names:**
            - Date: "Date", "Trans Date", "Transaction Date", "Posted Date"
            - Description: "Description", "Memo", "Details", "Merchant"
            - Amount: "Debit"/"Credit" or single "Amount" column
            """)
