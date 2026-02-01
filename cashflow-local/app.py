"""
CashFlow-Local: Local-First Money Manager

Main Streamlit application entry point.

Author: Antigravity AI
License: MIT
"""

import streamlit as st
import logging
import os

# Import UI pages
from src.ui.upload_page import render_upload_page
from src.ui.dashboard_page import render_dashboard_page
from src.ui.transactions_page import render_transactions_page
from src.ui.budgets_page import render_budgets_page
from src.ui.reports_page import render_reports_page

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="CashFlow-Local",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .stMetric {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
        }
        .stButton>button {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar navigation."""
    with st.sidebar:
        st.title("💰 CashFlow-Local")
        st.markdown("---")
        
        # Navigation
        page = st.radio(
            "Navigation",
            options=["📊 Dashboard", "📤 Upload", "💳 Transactions", "💰 Budgets", "📄 Reports"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Info section
        st.markdown("### ℹ️ About")
        st.markdown("""
        **CashFlow-Local** is a privacy-first financial manager.
        
        All your data stays local on your machine.
        
        **Features:**
        - 📤 Upload CSV/PDF statements
        - 🔄 Automatic deduplication
        - 🤖 Smart categorization
        - 📊 Visual analytics
        - 💰 Budget tracking
        - 📄 PDF/Excel Reports
        """)
        
        st.markdown("---")
        st.caption("Built with Streamlit & DuckDB")
        st.caption("© 2026 CashFlow-Local")
    
    return page


def main():
    """Main application entry point."""
    configure_page()
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Render selected page
    if selected_page == "📊 Dashboard":
        render_dashboard_page()
    elif selected_page == "📤 Upload":
        render_upload_page()
    elif selected_page == "💳 Transactions":
        render_transactions_page()
    elif selected_page == "💰 Budgets":
        render_budgets_page()
    elif selected_page == "📄 Reports":
        render_reports_page()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check the logs for more details.")
