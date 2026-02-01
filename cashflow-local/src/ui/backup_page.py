"""
Backup & Restore Page for CashFlow-Local Streamlit App

Provides UI for:
- Manual database backup (download)
- Database restore (upload)
- Backup validation and preview
- Restore mode selection (full, merge, selective)
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Optional

from src.backup import backup_manager

logger = logging.getLogger(__name__)


def render_backup_section():
    """Render the backup section of the page."""
    st.header("💾 Create Backup")
    
    st.markdown("""
    Create a backup of your entire database. The backup includes:
    - All transactions
    - Category rules
    - Budget settings
    
    The backup is compressed and includes validation checksums.
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📥 Download Backup", type="primary", use_container_width=True):
            try:
                with st.spinner("Creating backup..."):
                    # Create backup
                    zip_bytes, metadata = backup_manager.create_backup()
                    
                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"cashflow_backup_{timestamp}.zip"
                    
                    # Show success message with stats
                    st.success("✅ Backup created successfully!")
                    
                    # Display statistics
                    stats = metadata.get('statistics', {})
                    st.info(f"""
                    **Backup Contents:**
                    - Transactions: {stats.get('total_transactions', 0)}
                    - Category Rules: {stats.get('total_category_rules', 0)}
                    - Budgets: {stats.get('total_budgets', 0)}
                    """)
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Download Backup File",
                        data=zip_bytes,
                        file_name=filename,
                        mime="application/zip",
                        use_container_width=True
                    )
            
            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                st.error(f"❌ Backup failed: {str(e)}")
    
    with col2:
        st.info("""
        **💡 Tip:**
        
        Download backups regularly to protect your data.
        
        Store backups in a safe location outside this application.
        """)


def render_restore_section():
    """Render the restore section of the page."""
    st.header("📤 Restore from Backup")
    
    st.markdown("""
    Restore your database from a previously created backup file.
    
    **⚠️ Warning:** Depending on the restore mode selected, this may modify or replace your current data.
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Backup File",
        type=['zip'],
        help="Select a backup ZIP file created by this application"
    )
    
    if uploaded_file is not None:
        # Read file bytes
        zip_bytes = uploaded_file.read()
        
        # Validate and preview backup
        st.subheader("📋 Backup Preview")
        
        with st.spinner("Validating backup..."):
            is_valid, message, backup_data = backup_manager.validate_backup(zip_bytes)
        
        if not is_valid:
            st.error(f"❌ Invalid backup file: {message}")
            return
        
        st.success(f"✅ {message}")
        
        # Show preview
        preview = backup_manager.get_backup_preview(zip_bytes)
        if preview:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Transactions",
                    preview['statistics'].get('total_transactions', 0)
                )
            
            with col2:
                st.metric(
                    "Category Rules",
                    preview['statistics'].get('total_category_rules', 0)
                )
            
            with col3:
                st.metric(
                    "Budgets",
                    preview['statistics'].get('total_budgets', 0)
                )
            
            # Date range
            if preview['date_range']['earliest']:
                st.info(f"""
                **Date Range:** {preview['date_range']['earliest']} to {preview['date_range']['latest']}
                
                **Backup Created:** {preview['backup_date']}
                """)
        
        # Restore mode selection
        st.subheader("🔧 Restore Options")
        
        restore_mode = st.radio(
            "Select Restore Mode",
            options=["merge", "full", "selective"],
            format_func=lambda x: {
                "merge": "🔄 Merge - Add new data without removing existing",
                "full": "⚠️ Full Replace - Delete all current data and restore backup",
                "selective": "📅 Selective - Restore specific date range"
            }[x],
            help="""
            - **Merge:** Adds backup data to current database, skipping duplicates
            - **Full:** Deletes all current data and restores from backup
            - **Selective:** Restores only transactions within a specific date range
            """
        )
        
        # Selective mode date inputs
        start_date = None
        end_date = None
        if restore_mode == "selective":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=None,
                    help="Restore transactions from this date onwards"
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=None,
                    help="Restore transactions up to this date"
                )
            
            if start_date:
                start_date = start_date.isoformat()
            if end_date:
                end_date = end_date.isoformat()
        
        # Confirmation and restore
        st.markdown("---")
        
        if restore_mode == "full":
            st.warning("""
            ⚠️ **WARNING: Full Replace Mode**
            
            This will **DELETE ALL** your current data and replace it with the backup.
            
            Make sure you have a recent backup of your current data before proceeding!
            """)
            
            confirm = st.checkbox("I understand that this will delete all my current data")
            
            if not confirm:
                st.stop()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔄 Restore Database", type="primary", use_container_width=True):
                try:
                    with st.spinner("Restoring database..."):
                        success, message, stats = backup_manager.restore_backup(
                            zip_bytes,
                            mode=restore_mode,
                            start_date=start_date,
                            end_date=end_date
                        )
                    
                    if success:
                        st.success(f"✅ {message}")
                        
                        # Show statistics
                        st.info(f"""
                        **Restore Summary:**
                        - Transactions restored: {stats.get('transactions_restored', 0)}
                        - Category rules restored: {stats.get('category_rules_restored', 0)}
                        - Budgets restored: {stats.get('budgets_restored', 0)}
                        - Duplicates skipped: {stats.get('duplicates_skipped', 0)}
                        """)
                        
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")
                
                except Exception as e:
                    logger.error(f"Restore failed: {e}")
                    st.error(f"❌ Restore failed: {str(e)}")


def render_backup_page():
    """Main render function for backup & restore page."""
    st.title("💾 Backup & Restore")
    
    st.markdown("""
    Protect your financial data with backups. Create backups to download and store safely,
    or restore from a previous backup.
    """)
    
    st.markdown("---")
    
    # Create tabs for backup and restore
    tab1, tab2 = st.tabs(["📥 Create Backup", "📤 Restore Backup"])
    
    with tab1:
        render_backup_section()
    
    with tab2:
        render_restore_section()
    
    # Information section
    st.markdown("---")
    st.markdown("### ℹ️ About Backups")
    
    with st.expander("📖 Backup Information"):
        st.markdown("""
        #### What's included in a backup?
        
        A backup contains:
        - **All transactions** - Every financial transaction in your database
        - **Category rules** - Your custom categorization rules
        - **Budget settings** - All budget configurations
        
        #### Backup format
        
        - **Format:** Compressed ZIP file containing JSON data
        - **Validation:** SHA-256 checksum for integrity verification
        - **Portability:** JSON format ensures compatibility across systems
        
        #### Restore modes
        
        - **Merge Mode:** Safest option - adds backup data without deleting current data
        - **Full Replace:** Replaces all data with backup (use with caution!)
        - **Selective Restore:** Choose specific date range to restore
        
        #### Best practices
        
        1. **Regular backups:** Create backups weekly or before major changes
        2. **Multiple locations:** Store backups in different locations (external drive, cloud)
        3. **Test restores:** Periodically test your backups to ensure they work
        4. **Before updates:** Always backup before updating the application
        """)
    
    with st.expander("🔒 Security & Privacy"):
        st.markdown("""
        #### Data Security
        
        - **Local-first:** All backups are created locally on your machine
        - **No cloud upload:** Your data is never automatically uploaded anywhere
        - **Manual control:** You decide where to store your backups
        
        #### Future enhancements
        
        Planned features for future versions:
        - Encryption with password protection
        - Automated scheduled backups
        - Cloud storage integration (optional)
        - Incremental backups for efficiency
        """)
