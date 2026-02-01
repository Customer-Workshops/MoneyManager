"""
Activity Log Page

Displays workspace activity and audit trail.

Author: Antigravity AI
License: MIT
"""

import streamlit as st
import logging
import pandas as pd
from src.database import db_manager
from src.workspace import WorkspaceManager
from src.ui.auth_page import get_current_user, get_current_workspace

logger = logging.getLogger(__name__)


def render_activity_page():
    """Render the activity log page."""
    user = get_current_user()
    workspace = get_current_workspace()
    
    if not user or not workspace:
        st.error("Please log in to access this page")
        return
    
    st.title("📋 Activity Log")
    st.markdown(f"### {workspace['workspace_name']}")
    
    workspace_manager = WorkspaceManager(db_manager)
    
    # Filters
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("#### Recent Activity")
    
    with col2:
        limit = st.selectbox("Show", options=[25, 50, 100], index=1)
    
    try:
        activities = workspace_manager.get_activity_log(workspace['workspace_id'], limit)
        
        if activities:
            # Convert to DataFrame for better display
            df = pd.DataFrame(activities)
            
            # Format the display
            for activity in activities:
                col1, col2, col3 = st.columns([2, 3, 2])
                
                with col1:
                    st.markdown(f"**{activity['user_name']}**")
                    st.caption(activity['user_email'])
                
                with col2:
                    action_emoji = {
                        'created': '➕',
                        'updated': '✏️',
                        'deleted': '🗑️',
                        'uploaded': '📤'
                    }
                    emoji = action_emoji.get(activity['action'], '📝')
                    
                    st.markdown(f"{emoji} **{activity['action'].title()}** {activity['entity_type']}")
                    if activity['description']:
                        st.caption(activity['description'])
                
                with col3:
                    st.caption(str(activity['created_at']))
                
                st.markdown("---")
        else:
            st.info("No activity yet. Start using the app to see activity here!")
    
    except Exception as e:
        logger.error(f"Error loading activity log: {e}")
        st.error(f"Failed to load activity log: {str(e)}")
