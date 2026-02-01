"""
Authentication UI Page

Provides login and registration interface for multi-user support.

Author: Antigravity AI
License: MIT
"""

import streamlit as st
import logging
from src.database import db_manager
from src.auth import AuthService

logger = logging.getLogger(__name__)


def init_session_state():
    """Initialize session state variables for authentication."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_workspace' not in st.session_state:
        st.session_state.current_workspace = None


def render_login_page():
    """Render login and registration page."""
    init_session_state()
    
    st.title("💰 CashFlow-Local")
    st.markdown("### Welcome to Your Family Money Manager")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    auth_service = AuthService(db_manager)
    
    with tab1:
        render_login_form(auth_service)
    
    with tab2:
        render_registration_form(auth_service)


def render_login_form(auth_service):
    """Render login form."""
    st.markdown("#### Sign in to your account")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("Please enter both email and password")
                return
            
            try:
                user_info = auth_service.login(email, password)
                
                if user_info:
                    st.session_state.authenticated = True
                    st.session_state.user = user_info
                    
                    # Set default workspace (first one)
                    if user_info['workspaces']:
                        st.session_state.current_workspace = user_info['workspaces'][0]
                    
                    st.success(f"Welcome back, {user_info['full_name']}! 👋")
                    st.rerun()
                else:
                    st.error("Invalid email or password")
            
            except Exception as e:
                logger.error(f"Login error: {e}")
                st.error(f"Login failed: {str(e)}")


def render_registration_form(auth_service):
    """Render registration form."""
    st.markdown("#### Create a new account")
    
    with st.form("registration_form"):
        full_name = st.text_input("Full Name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="john.doe@example.com")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")
        workspace_name = st.text_input(
            "Family/Workspace Name (Optional)",
            placeholder="The Doe Family"
        )
        
        submit = st.form_submit_button("Create Account", use_container_width=True)
        
        if submit:
            # Validate inputs
            if not full_name or not email or not password:
                st.error("Please fill in all required fields")
                return
            
            if password != password_confirm:
                st.error("Passwords do not match")
                return
            
            if len(password) < 6:
                st.error("Password must be at least 6 characters long")
                return
            
            try:
                user_info = auth_service.register_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    workspace_name=workspace_name if workspace_name else None
                )
                
                # Auto-login after registration
                st.session_state.authenticated = True
                st.session_state.user = {
                    'user_id': user_info['user_id'],
                    'email': user_info['email'],
                    'full_name': user_info['full_name'],
                    'workspaces': [{
                        'workspace_id': user_info['workspace_id'],
                        'workspace_name': user_info['workspace_name'],
                        'role': user_info['role']
                    }]
                }
                st.session_state.current_workspace = {
                    'workspace_id': user_info['workspace_id'],
                    'workspace_name': user_info['workspace_name'],
                    'role': user_info['role']
                }
                
                st.success(f"Account created successfully! Welcome, {full_name}! 🎉")
                st.rerun()
            
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                logger.error(f"Registration error: {e}")
                st.error(f"Registration failed: {str(e)}")


def logout():
    """Logout user and clear session state."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_workspace = None
    st.rerun()


def require_auth():
    """
    Decorator-like function to require authentication.
    Call this at the start of any page that requires login.
    
    Returns:
        True if authenticated, False otherwise (and shows login page)
    """
    init_session_state()
    
    if not st.session_state.authenticated:
        render_login_page()
        return False
    
    return True


def get_current_user():
    """
    Get current logged-in user.
    
    Returns:
        User info dictionary or None
    """
    init_session_state()
    return st.session_state.user


def get_current_workspace():
    """
    Get current active workspace.
    
    Returns:
        Workspace info dictionary or None
    """
    init_session_state()
    return st.session_state.current_workspace


def set_current_workspace(workspace_id: int):
    """
    Switch to a different workspace.
    
    Args:
        workspace_id: Workspace ID to switch to
    """
    user = get_current_user()
    if user:
        for workspace in user['workspaces']:
            if workspace['workspace_id'] == workspace_id:
                st.session_state.current_workspace = workspace
                st.rerun()
                break
