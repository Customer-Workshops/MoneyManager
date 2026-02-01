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
from src.ui.accounts_page import render_accounts_page
# from src.ui.insights_page import render_insights_page  # TODO: Implement

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
        st.title("💸 CashFlow")
        
        # TODO: Implement multi-user authentication
        # user = get_current_user()
        # workspace = get_current_workspace()
        # ...
       
        # Navigation
        selected_page = st.radio(
            "Navigate",
            options=["Calendar", "Dashboard", "Upload", "Accounts", "Bill Manager", "Settings"],
            index=0,  # Default to Calendar
            format_func=lambda x: {
                "Calendar": "📅 Calendar",
                "Dashboard": "📊 Stats",
                "Upload": "📤 Import",
                "Accounts": "🏦 Assets",
                "Bill Manager": "📅 Bills",
                "Settings": "⚙️ Settings"
            }.get(x, x)
        )
        
        st.divider()
        st.caption(f"v1.0.0 (Realbyte Style)")

    return selected_page


def main():
    """Main application entry point."""
    configure_page()
    
    # TODO: Implement authentication
    # if not require_auth():
    #     return
    
    # Inject Material Icons for Calendar View
    st.markdown('<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">', unsafe_allow_html=True)
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Render selected page
    if selected_page == "Calendar":
        from src.ui.calendar_view import render_calendar_view
        render_calendar_view()
        
    elif selected_page == "Dashboard":
        from src.ui.stats_view import render_stats_view
        render_stats_view()
        
    elif selected_page == "Upload":
        render_upload_page()
        
    elif selected_page == "Accounts":
        render_accounts_page()
        
    elif selected_page == "Bill Manager":
        st.info("🚧 Bill Manager coming soon")
        
    elif selected_page == "Settings":
        st.title("⚙️ Settings")
        if st.button("RESET DATABASE (Dev)"):
            try:
                # Simple nuking for dev
                db_manager.execute_query("DROP TABLE IF EXISTS transactions")
                db_manager.execute_query("DROP TABLE IF EXISTS categories")
                db_manager.execute_query("DROP TABLE IF EXISTS accounts") # Re-create accounts logic
                db_manager._initialize_schema()
                st.success("Database Reset! Please refresh.")
            except Exception as e:
                st.error(f"Reset failed: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check the logs for more details.")
