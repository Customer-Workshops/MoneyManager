"""
Goals Page for CashFlow-Local Streamlit App

Provides interface for managing financial goals and tracking progress.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import logging

from src.goals import (
    GOAL_TYPES, create_goal, add_contribution, get_all_goals,
    get_goal_by_id, get_goal_contributions, update_goal, delete_goal
)

logger = logging.getLogger(__name__)


def render_goals_page():
    """Render the financial goals management page."""
    st.title("🎯 Financial Goals & Savings Tracker")
    st.markdown("Track your savings goals and monitor your progress")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📊 My Goals", "➕ Create Goal", "📈 Analytics"])
    
    with tab1:
        render_goals_list()
    
    with tab2:
        render_create_goal_form()
    
    with tab3:
        render_goals_analytics()


def render_goals_list():
    """Render list of all goals with progress tracking."""
    st.subheader("My Financial Goals")
    
    goals = get_all_goals()
    
    if not goals:
        st.info("📋 No goals yet. Create your first goal to start tracking!")
        return
    
    # Display each goal in an expandable card
    for goal in goals:
        render_goal_card(goal)


def render_goal_card(goal: dict):
    """
    Render an individual goal card with progress and actions.
    
    Args:
        goal: Goal dictionary with metrics
    """
    # Goal header with expander
    goal_icon = get_goal_icon(goal['goal_type'])
    header = f"{goal_icon} {goal['name']} - {goal['milestone']}"
    
    with st.expander(header, expanded=False):
        # Progress bar
        progress = goal['progress_percent'] / 100
        st.progress(progress)
        
        # Goal details in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "💰 Target Amount",
                f"₹{goal['target_amount']:,.2f}",
            )
            st.metric(
                "📅 Target Date",
                goal['target_date'].strftime('%b %d, %Y') if isinstance(goal['target_date'], date) else goal['target_date']
            )
        
        with col2:
            st.metric(
                "💵 Current Savings",
                f"₹{goal['current_amount']:,.2f}",
                delta=f"{goal['progress_percent']:.1f}%"
            )
            st.metric(
                "⏱️ Time Remaining",
                f"{goal['days_remaining']} days" if goal['days_remaining'] >= 0 else "Overdue"
            )
        
        with col3:
            st.metric(
                "💸 Remaining",
                f"₹{goal['remaining_amount']:,.2f}"
            )
            st.metric(
                "📊 Monthly Required",
                f"₹{goal['required_monthly']:,.2f}"
            )
        
        # Status indicators
        st.markdown("---")
        col_status1, col_status2, col_status3 = st.columns(3)
        
        with col_status1:
            status_color = "🟢" if goal['is_on_track'] else "🔴"
            st.markdown(f"**Status:** {status_color} {'On Track' if goal['is_on_track'] else 'Behind Schedule'}")
        
        with col_status2:
            st.markdown(f"**Priority:** {'⭐' * min(goal['priority'], 5)}")
        
        with col_status3:
            if goal['projected_date']:
                proj_date = goal['projected_date'].strftime('%b %d, %Y')
                st.markdown(f"**Projected Completion:** {proj_date}")
        
        # Action buttons
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button("💰 Add Contribution", key=f"contrib_{goal['id']}"):
                st.session_state[f'show_contrib_form_{goal["id"]}'] = True
        
        with col_btn2:
            if st.button("📝 Edit Goal", key=f"edit_{goal['id']}"):
                st.session_state[f'show_edit_form_{goal["id"]}'] = True
        
        with col_btn3:
            if st.button("📜 View History", key=f"history_{goal['id']}"):
                st.session_state[f'show_history_{goal["id"]}'] = True
        
        with col_btn4:
            if st.button("🗑️ Delete", key=f"delete_{goal['id']}", type="secondary"):
                if delete_goal(goal['id']):
                    st.success(f"Goal '{goal['name']}' deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete goal")
        
        # Show contribution form if triggered
        if st.session_state.get(f'show_contrib_form_{goal["id"]}', False):
            render_contribution_form(goal)
        
        # Show edit form if triggered
        if st.session_state.get(f'show_edit_form_{goal["id"]}', False):
            render_edit_goal_form(goal)
        
        # Show history if triggered
        if st.session_state.get(f'show_history_{goal["id"]}', False):
            render_contribution_history(goal)


def render_contribution_form(goal: dict):
    """
    Render form to add a contribution to a goal.
    
    Args:
        goal: Goal dictionary
    """
    st.markdown("#### Add Contribution")
    
    with st.form(key=f"contrib_form_{goal['id']}"):
        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            value=1000.0,
            step=100.0,
            key=f"contrib_amount_{goal['id']}"
        )
        
        contrib_date = st.date_input(
            "Contribution Date",
            value=date.today(),
            key=f"contrib_date_{goal['id']}"
        )
        
        notes = st.text_input(
            "Notes (optional)",
            key=f"contrib_notes_{goal['id']}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("💰 Add Contribution", type="primary")
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if submit:
            if add_contribution(goal['id'], amount, contrib_date, notes):
                st.success(f"Added ₹{amount:,.2f} to {goal['name']}!")
                st.session_state[f'show_contrib_form_{goal["id"]}'] = False
                st.rerun()
            else:
                st.error("Failed to add contribution")
        
        if cancel:
            st.session_state[f'show_contrib_form_{goal["id"]}'] = False
            st.rerun()


def render_edit_goal_form(goal: dict):
    """
    Render form to edit goal details.
    
    Args:
        goal: Goal dictionary
    """
    st.markdown("#### Edit Goal")
    
    with st.form(key=f"edit_form_{goal['id']}"):
        name = st.text_input("Goal Name", value=goal['name'])
        
        target_amount = st.number_input(
            "Target Amount (₹)",
            min_value=1.0,
            value=float(goal['target_amount']),
            step=1000.0
        )
        
        target_date_val = goal['target_date']
        if isinstance(target_date_val, str):
            target_date_val = datetime.strptime(target_date_val, '%Y-%m-%d').date()
        
        target_date = st.date_input(
            "Target Date",
            value=target_date_val
        )
        
        priority = st.slider(
            "Priority (1 = Highest)",
            min_value=1,
            max_value=10,
            value=goal['priority']
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("💾 Save Changes", type="primary")
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if submit:
            if update_goal(goal['id'], name, target_amount, target_date, priority):
                st.success(f"Updated goal '{name}'!")
                st.session_state[f'show_edit_form_{goal["id"]}'] = False
                st.rerun()
            else:
                st.error("Failed to update goal")
        
        if cancel:
            st.session_state[f'show_edit_form_{goal["id"]}'] = False
            st.rerun()


def render_contribution_history(goal: dict):
    """
    Render contribution history for a goal.
    
    Args:
        goal: Goal dictionary
    """
    st.markdown("#### Contribution History")
    
    contributions = get_goal_contributions(goal['id'])
    
    if not contributions:
        st.info("No contributions yet")
    else:
        # Convert to DataFrame for display
        df = pd.DataFrame(contributions)
        df['amount'] = df['amount'].apply(lambda x: f"₹{float(x):,.2f}")
        df['contribution_date'] = pd.to_datetime(df['contribution_date']).dt.strftime('%Y-%m-%d')
        
        # Display table
        st.dataframe(
            df[['contribution_date', 'amount', 'notes']],
            use_container_width=True,
            hide_index=True
        )
    
    if st.button("Close History", key=f"close_history_{goal['id']}"):
        st.session_state[f'show_history_{goal["id"]}'] = False
        st.rerun()


def render_create_goal_form():
    """Render form to create a new financial goal."""
    st.subheader("Create a New Financial Goal")
    
    with st.form("create_goal_form"):
        # Goal name
        name = st.text_input(
            "Goal Name *",
            placeholder="e.g., Emergency Fund, Vacation to Europe",
            help="Give your goal a descriptive name"
        )
        
        # Goal type
        goal_type = st.selectbox(
            "Goal Type *",
            options=GOAL_TYPES,
            help="Select the category that best matches your goal"
        )
        
        # Target amount
        target_amount = st.number_input(
            "Target Amount (₹) *",
            min_value=1.0,
            value=100000.0,
            step=1000.0,
            help="How much do you want to save?"
        )
        
        # Target date
        target_date = st.date_input(
            "Target Date *",
            value=date.today() + timedelta(days=365),
            min_value=date.today(),
            help="When do you want to achieve this goal?"
        )
        
        # Priority
        priority = st.slider(
            "Priority",
            min_value=1,
            max_value=10,
            value=5,
            help="1 = Highest priority, 10 = Lowest priority"
        )
        
        # Submit button
        submitted = st.form_submit_button("🎯 Create Goal", type="primary")
        
        if submitted:
            if not name:
                st.error("Please provide a goal name")
            else:
                goal_id = create_goal(name, goal_type, target_amount, target_date, priority)
                if goal_id:
                    st.success(f"✅ Goal '{name}' created successfully!")
                    st.balloons()
                    
                    # Calculate required monthly savings
                    months = max((target_date - date.today()).days / 30.44, 1)
                    monthly_required = target_amount / months
                    
                    st.info(f"💡 You need to save approximately ₹{monthly_required:,.2f} per month to reach your goal by {target_date.strftime('%B %d, %Y')}")
                    
                    # Clear form by rerunning
                    st.rerun()
                else:
                    st.error("Failed to create goal. Please try again.")


def render_goals_analytics():
    """Render analytics and visualizations for all goals."""
    st.subheader("Goals Analytics & Insights")
    
    goals = get_all_goals()
    
    if not goals:
        st.info("📊 No data to display. Create goals to see analytics!")
        return
    
    # Overall statistics
    st.markdown("### 📈 Overall Progress")
    
    total_target = sum(g['target_amount'] for g in goals)
    total_saved = sum(g['current_amount'] for g in goals)
    overall_progress = (total_saved / total_target * 100) if total_target > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Goals", len(goals))
    
    with col2:
        st.metric("Total Target", f"₹{total_target:,.2f}")
    
    with col3:
        st.metric("Total Saved", f"₹{total_saved:,.2f}")
    
    with col4:
        st.metric("Overall Progress", f"{overall_progress:.1f}%")
    
    # Goals by type chart
    st.markdown("### 📊 Goals by Type")
    
    df_goals = pd.DataFrame(goals)
    type_counts = df_goals['goal_type'].value_counts()
    
    fig_types = px.pie(
        values=type_counts.values,
        names=type_counts.index,
        title="Distribution of Goals by Type"
    )
    st.plotly_chart(fig_types, use_container_width=True)
    
    # Progress comparison chart
    st.markdown("### 📊 Progress Comparison")
    
    df_progress = pd.DataFrame([
        {
            'Goal': g['name'],
            'Progress': g['progress_percent'],
            'Status': 'On Track' if g['is_on_track'] else 'Behind'
        }
        for g in goals
    ])
    
    fig_progress = px.bar(
        df_progress,
        x='Goal',
        y='Progress',
        color='Status',
        title="Progress Towards Each Goal",
        labels={'Progress': 'Progress (%)'},
        color_discrete_map={'On Track': '#00CC96', 'Behind': '#EF553B'}
    )
    fig_progress.update_layout(showlegend=True)
    st.plotly_chart(fig_progress, use_container_width=True)
    
    # Timeline view
    st.markdown("### 📅 Goals Timeline")
    
    df_timeline = pd.DataFrame([
        {
            'Goal': g['name'],
            'Start': g['created_at'].date() if isinstance(g['created_at'], datetime) else g['created_at'],
            'Target': g['target_date'] if isinstance(g['target_date'], date) else datetime.strptime(g['target_date'], '%Y-%m-%d').date(),
            'Status': 'Completed' if g['progress_percent'] >= 100 else ('On Track' if g['is_on_track'] else 'Behind')
        }
        for g in goals
    ])
    
    fig_timeline = px.timeline(
        df_timeline,
        x_start='Start',
        x_end='Target',
        y='Goal',
        color='Status',
        title="Goal Timeline View",
        color_discrete_map={'Completed': '#00CC96', 'On Track': '#636EFA', 'Behind': '#EF553B'}
    )
    fig_timeline.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_timeline, use_container_width=True)


def get_goal_icon(goal_type: str) -> str:
    """
    Get emoji icon for goal type.
    
    Args:
        goal_type: Goal type
    
    Returns:
        Emoji icon
    """
    icons = {
        "Emergency Fund": "🚨",
        "Vacation/Travel": "✈️",
        "New Car/Bike": "🚗",
        "Home Down Payment": "🏠",
        "Education": "🎓",
        "Retirement": "🏖️",
        "Custom": "🎯"
    }
    return icons.get(goal_type, "🎯")
