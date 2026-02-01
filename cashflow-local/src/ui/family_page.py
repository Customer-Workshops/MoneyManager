"""
Family/Workspace Management Page

Provides UI for managing workspace members, accounts, and goals.

Author: Antigravity AI
License: MIT
"""

import streamlit as st
import logging
from src.database import db_manager
from src.auth import AuthService
from src.workspace import WorkspaceManager
from src.ui.auth_page import get_current_user, get_current_workspace

logger = logging.getLogger(__name__)


def render_family_page():
    """Render the family/workspace management page."""
    user = get_current_user()
    workspace = get_current_workspace()
    
    if not user or not workspace:
        st.error("Please log in to access this page")
        return
    
    st.title("👥 Family Management")
    st.markdown(f"### {workspace['workspace_name']}")
    
    workspace_manager = WorkspaceManager(db_manager)
    auth_service = AuthService(db_manager)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Members", "🏦 Accounts", "🎯 Goals", "⚙️ Settings"])
    
    with tab1:
        render_members_tab(workspace, user, workspace_manager, auth_service)
    
    with tab2:
        render_accounts_tab(workspace, user, workspace_manager)
    
    with tab3:
        render_goals_tab(workspace, user, workspace_manager)
    
    with tab4:
        render_settings_tab(workspace, user)


def render_members_tab(workspace, user, workspace_manager, auth_service):
    """Render workspace members management."""
    st.markdown("#### Workspace Members")
    
    try:
        members = workspace_manager.get_workspace_members(workspace['workspace_id'])
        
        # Display members
        for member in members:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.markdown(f"**{member['full_name']}**")
                st.caption(member['email'])
            
            with col2:
                # Role badge
                role_emoji = {"Admin": "👑", "Editor": "✏️", "Viewer": "👁️"}
                st.markdown(f"{role_emoji.get(member['role'], '👤')} {member['role']}")
            
            with col3:
                # Update role (only for admins)
                if workspace['role'] == 'Admin' and member['user_id'] != user['user_id']:
                    new_role = st.selectbox(
                        "Change role",
                        options=['Admin', 'Editor', 'Viewer'],
                        index=['Admin', 'Editor', 'Viewer'].index(member['role']),
                        key=f"role_{member['user_id']}",
                        label_visibility="collapsed"
                    )
                    
                    if new_role != member['role']:
                        if st.button("Update", key=f"update_{member['user_id']}"):
                            try:
                                workspace_manager.update_member_role(
                                    workspace['workspace_id'],
                                    member['user_id'],
                                    new_role,
                                    user['user_id']
                                )
                                st.success(f"Updated {member['full_name']}'s role to {new_role}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update role: {str(e)}")
            
            with col4:
                # Remove member (only for admins, not self)
                if workspace['role'] == 'Admin' and member['user_id'] != user['user_id']:
                    if st.button("Remove", key=f"remove_{member['user_id']}", type="secondary"):
                        try:
                            workspace_manager.remove_member(
                                workspace['workspace_id'],
                                member['user_id'],
                                user['user_id']
                            )
                            st.success(f"Removed {member['full_name']} from workspace")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to remove member: {str(e)}")
            
            st.markdown("---")
        
        # Invite new member (only for admins)
        if workspace['role'] == 'Admin':
            st.markdown("#### Invite New Member")
            
            with st.form("invite_form"):
                col1, col2 = st.columns(2)
                with col1:
                    invite_email = st.text_input("Email Address")
                with col2:
                    invite_role = st.selectbox("Role", options=['Editor', 'Viewer', 'Admin'])
                
                submit = st.form_submit_button("Send Invite", use_container_width=True)
                
                if submit:
                    if not invite_email:
                        st.error("Please enter an email address")
                    else:
                        try:
                            auth_service.invite_user(
                                workspace['workspace_id'],
                                invite_email,
                                invite_role,
                                user['user_id']
                            )
                            st.success(f"Invited {invite_email} as {invite_role}")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Failed to send invite: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error loading members: {e}")
        st.error(f"Failed to load members: {str(e)}")


def render_accounts_tab(workspace, user, workspace_manager):
    """Render accounts management."""
    st.markdown("#### Accounts")
    
    try:
        accounts = workspace_manager.get_accounts(workspace['workspace_id'], user['user_id'])
        
        # Display accounts
        if accounts:
            for account in accounts:
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.markdown(f"**{account['name']}**")
                    st.caption(account['account_type'])
                
                with col2:
                    if account['is_shared']:
                        st.markdown("🌐 Shared")
                    else:
                        st.markdown("🔒 Personal")
                
                with col3:
                    # Placeholder for account actions
                    pass
                
                st.markdown("---")
        else:
            st.info("No accounts yet. Create your first account below!")
        
        # Create new account (only for admins and editors)
        if workspace['role'] in ['Admin', 'Editor']:
            st.markdown("#### Create New Account")
            
            with st.form("account_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    account_name = st.text_input("Account Name", placeholder="e.g., Joint Checking")
                    account_type = st.selectbox(
                        "Account Type",
                        options=['Checking', 'Savings', 'Credit Card', 'Cash', 'Investment']
                    )
                
                with col2:
                    is_shared = st.checkbox("Shared Account", value=True)
                    if not is_shared:
                        st.info("Personal accounts are only visible to you")
                
                submit = st.form_submit_button("Create Account", use_container_width=True)
                
                if submit:
                    if not account_name:
                        st.error("Please enter an account name")
                    else:
                        try:
                            account_id = workspace_manager.create_account(
                                workspace['workspace_id'],
                                account_name,
                                account_type,
                                is_shared,
                                None if is_shared else user['user_id']
                            )
                            st.success(f"Created account: {account_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to create account: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error loading accounts: {e}")
        st.error(f"Failed to load accounts: {str(e)}")


def render_goals_tab(workspace, user, workspace_manager):
    """Render savings goals management."""
    st.markdown("#### Savings Goals")
    
    try:
        goals = workspace_manager.get_goals(workspace['workspace_id'])
        
        # Display goals
        if goals:
            for goal in goals:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{goal['name']}**")
                    progress = goal['progress_percent']
                    st.progress(min(progress / 100, 1.0))
                    st.caption(f"${goal['current_amount']:,.2f} of ${goal['target_amount']:,.2f} ({progress:.1f}%)")
                    
                    if goal['target_date']:
                        st.caption(f"Target: {goal['target_date']}")
                
                with col2:
                    if goal['is_shared']:
                        st.markdown("🌐 Shared")
                    else:
                        st.markdown("🔒 Personal")
                
                st.markdown("---")
        else:
            st.info("No goals yet. Create your first savings goal below!")
        
        # Create new goal (only for admins and editors)
        if workspace['role'] in ['Admin', 'Editor']:
            st.markdown("#### Create New Goal")
            
            with st.form("goal_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    goal_name = st.text_input("Goal Name", placeholder="e.g., Family Vacation")
                    target_amount = st.number_input("Target Amount ($)", min_value=0.0, step=100.0)
                
                with col2:
                    target_date = st.date_input("Target Date (Optional)", value=None)
                    is_shared = st.checkbox("Shared Goal", value=True)
                
                submit = st.form_submit_button("Create Goal", use_container_width=True)
                
                if submit:
                    if not goal_name or target_amount <= 0:
                        st.error("Please enter a valid goal name and target amount")
                    else:
                        try:
                            goal_id = workspace_manager.create_goal(
                                workspace['workspace_id'],
                                goal_name,
                                target_amount,
                                target_date if target_date else None,
                                is_shared,
                                user['user_id']
                            )
                            st.success(f"Created goal: {goal_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to create goal: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error loading goals: {e}")
        st.error(f"Failed to load goals: {str(e)}")


def render_settings_tab(workspace, user):
    """Render workspace settings."""
    st.markdown("#### Workspace Settings")
    
    st.info("Workspace settings will be available in a future update.")
    
    st.markdown("**Current Settings:**")
    st.markdown(f"- **Workspace Name:** {workspace['workspace_name']}")
    st.markdown(f"- **Your Role:** {workspace['role']}")
    st.markdown(f"- **Workspace ID:** {workspace['workspace_id']}")
