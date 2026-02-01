"""
AI-Powered Insights Dashboard Page for CashFlow-Local

Displays smart insights, spending recommendations, and financial health score.

Author: Antigravity AI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import logging

from src.database import db_manager
from src.insights import get_insights_engine

logger = logging.getLogger(__name__)


def render_insights_page():
    """Render the AI-powered insights dashboard page."""
    st.title("🤖 AI-Powered Smart Insights")
    st.markdown("Get personalized financial insights and actionable recommendations")
    st.markdown("---")
    
    # Initialize insights engine
    engine = get_insights_engine(db_manager)
    
    if not engine:
        st.error("Failed to initialize insights engine")
        return
    
    # Generate all insights
    with st.spinner("🔍 Analyzing your financial data..."):
        insights = engine.get_all_insights()
    
    # Display Financial Health Score
    render_health_score(insights['health_score'])
    
    st.markdown("---")
    
    # Display Top 3 Actionable Tips
    render_top_tips(insights['top_tips'])
    
    st.markdown("---")
    
    # Tabbed interface for different insight categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Spending Analysis",
        "📈 Trends",
        "🔮 Predictions",
        "💰 Savings",
        "🔁 Patterns"
    ])
    
    with tab1:
        render_spending_analysis(insights)
    
    with tab2:
        render_trends(insights['trends'])
    
    with tab3:
        render_predictions(insights['predictions'])
    
    with tab4:
        render_savings_opportunities(insights['savings_opportunities'])
    
    with tab5:
        render_patterns(insights['patterns'])


def render_health_score(health_score: dict):
    """Render Financial Health Score widget."""
    st.subheader("💯 Financial Health Score")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display score as a large metric
        score = health_score.get('score', 0)
        grade = health_score.get('grade', 'N/A')
        
        # Color-code based on score
        if score >= 80:
            color = "#28a745"  # Green
        elif score >= 60:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red
        
        st.markdown(f"""
            <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                <h1 style="color: {color}; font-size: 72px; margin: 0;">{score:.0f}</h1>
                <p style="font-size: 24px; margin: 0;">Grade: {grade}</p>
                <p style="font-size: 18px; color: #666; margin-top: 10px;">{health_score.get('message', '')}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Display score breakdown
        st.markdown("#### Score Breakdown")
        
        breakdown = health_score.get('breakdown', {})
        
        for component, data in breakdown.items():
            score_val = data.get('score', 0)
            max_score = data.get('max_score', 100)
            message = data.get('message', '')
            
            # Progress bar
            progress = score_val / max_score if max_score > 0 else 0
            
            # Color based on percentage
            if progress >= 0.8:
                bar_color = "🟢"
            elif progress >= 0.5:
                bar_color = "🟡"
            else:
                bar_color = "🔴"
            
            st.markdown(f"**{component.replace('_', ' ').title()}:** {score_val:.0f}/{max_score}")
            st.progress(progress)
            st.caption(f"{bar_color} {message}")
            st.markdown("")


def render_top_tips(tips: list):
    """Render top 3 actionable tips."""
    st.subheader("💡 Top 3 Actionable Tips")
    
    if not tips:
        st.info("No tips available yet. Upload more transactions to get insights!")
        return
    
    # Display tips in columns
    cols = st.columns(min(3, len(tips)))
    
    for idx, tip in enumerate(tips[:3]):
        with cols[idx]:
            st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 4px solid #2196f3;">
                    <p style="margin: 0; font-size: 14px;">{tip}</p>
                </div>
            """, unsafe_allow_html=True)


def render_spending_analysis(insights: dict):
    """Render spending anomalies and budget alerts."""
    st.subheader("📊 Spending Analysis")
    
    # Budget Alerts
    budget_alerts = insights.get('budget_alerts', [])
    if budget_alerts:
        st.markdown("#### ⚠️ Budget Alerts")
        for alert in budget_alerts:
            severity = alert.get('severity', 'warning')
            icon = "🔴" if severity == "critical" else "🟡"
            
            with st.expander(f"{icon} {alert['category']} - {alert['usage_percentage']:.0f}% used"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Budget Limit", f"${alert['budget_limit']:,.2f}")
                    st.metric("Current Spending", f"${alert['current_spending']:,.2f}")
                with col2:
                    st.metric("Usage", f"{alert['usage_percentage']:.1f}%")
                    remaining = alert['budget_limit'] - alert['current_spending']
                    st.metric("Remaining", f"${remaining:,.2f}")
                
                st.info(alert['message'])
    else:
        st.info("No budget alerts. Your spending is on track! 🎉")
    
    st.markdown("---")
    
    # Spending Anomalies
    anomalies = insights.get('anomalies', [])
    if anomalies:
        st.markdown("#### 🔍 Spending Anomalies")
        st.caption("Unusual spending patterns compared to your historical average")
        
        for anomaly in anomalies[:5]:  # Show top 5
            severity_icon = "🔴" if anomaly.get('severity') == 'high' else "🟡"
            
            with st.expander(f"{severity_icon} {anomaly['category']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Month", f"${anomaly['current_amount']:,.2f}")
                with col2:
                    st.metric("Historical Average", f"${anomaly['average_amount']:,.2f}")
                with col3:
                    change = anomaly['percentage_change']
                    st.metric("Change", f"{change:+.1f}%")
                
                st.markdown(anomaly['message'])
    else:
        st.info("No significant spending anomalies detected. Your spending is consistent! ✅")


def render_trends(trends: list):
    """Render spending trends over time."""
    st.subheader("📈 Spending Trends")
    st.caption("3-month spending trend analysis by category")
    
    if not trends:
        st.info("Not enough historical data to identify trends. Keep uploading transactions!")
        return
    
    for trend in trends[:5]:  # Show top 5 trends
        direction = trend['direction']
        icon = "📈" if direction == "increasing" else "📉"
        color = "#ff6b6b" if direction == "increasing" else "#51cf66"
        
        with st.expander(f"{icon} {trend['category']} - {abs(trend['percentage_change']):.0f}% {direction}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("3 Months Ago", f"${trend['oldest_amount']:,.2f}")
            with col2:
                st.metric("Current Month", f"${trend['newest_amount']:,.2f}")
            with col3:
                st.metric("Change", f"{trend['percentage_change']:+.1f}%")
            
            st.markdown(f"<p style='color: {color};'>{trend['message']}</p>", unsafe_allow_html=True)


def render_predictions(predictions: list):
    """Render spending predictions."""
    st.subheader("🔮 Spending Predictions")
    st.caption("Projected end-of-month spending based on current trends")
    
    if not predictions:
        st.info("Predictions will be available after a few days into the month.")
        return
    
    # Create a table view
    if predictions:
        df_predictions = pd.DataFrame(predictions)
        
        # Format for display
        display_df = pd.DataFrame({
            'Category': df_predictions['category'],
            'Spent So Far': df_predictions['amount_so_far'].apply(lambda x: f"${x:,.2f}"),
            'Projected Total': df_predictions['projected_amount'].apply(lambda x: f"${x:,.2f}"),
            'Days Remaining': df_predictions['days_remaining']
        })
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Show detailed predictions
        for pred in predictions[:3]:
            st.markdown(f"**{pred['category']}:** {pred['message']}")


def render_savings_opportunities(opportunities: list):
    """Render savings opportunities."""
    st.subheader("💰 Savings Opportunities")
    st.caption("Identified opportunities to reduce spending and save money")
    
    if not opportunities:
        st.info("No specific savings opportunities identified. Great job managing your spending! 👍")
        return
    
    total_potential_savings = 0
    
    for opp in opportunities:
        category_type = opp.get('category', 'general')
        
        if category_type == 'subscription':
            icon = "🔄"
            with st.expander(f"{icon} Recurring Subscription: {opp['description']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Monthly Cost", f"${opp['monthly_cost']:,.2f}")
                with col2:
                    st.metric("3-Month Total", f"${opp['total_cost_3m']:,.2f}")
                
                st.info(opp['message'])
                total_potential_savings += opp['monthly_cost']
        
        elif category_type == 'high_spending':
            icon = "💸"
            with st.expander(f"{icon} High Spending: {opp['spending_category']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current", f"${opp['current_amount']:,.2f}")
                with col2:
                    st.metric("Average", f"${opp['average_amount']:,.2f}")
                with col3:
                    st.metric("Potential Savings", f"${opp['potential_savings']:,.2f}")
                
                st.info(opp['message'])
                total_potential_savings += opp['potential_savings']
    
    if total_potential_savings > 0:
        st.success(f"💡 Total potential monthly savings: **${total_potential_savings:,.2f}**")


def render_patterns(patterns: dict):
    """Render detected spending patterns."""
    st.subheader("🔁 Spending Patterns")
    
    # Recurring Transactions
    recurring = patterns.get('recurring_transactions', [])
    if recurring:
        st.markdown("#### 🔄 Recurring Transactions")
        st.caption("Regular payments that could be automated")
        
        for trans in recurring[:5]:
            desc = trans['description']
            truncated_desc = f"{desc[:40]}{'...' if len(desc) > 40 else ''}"
            with st.expander(f"{truncated_desc} - ${trans['amount']:.2f} (x{trans['frequency']})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Amount", f"${trans['amount']:,.2f}")
                with col2:
                    st.metric("Frequency", f"{trans['frequency']} times")
                with col3:
                    st.metric("Category", trans['category'])
                
                st.info(f"💡 {trans['suggestion']}")
                st.caption(f"First: {trans['first_date']} | Last: {trans['last_date']}")
    else:
        st.info("No recurring transaction patterns detected.")
    
    st.markdown("---")
    
    # Potential Duplicates
    duplicates = patterns.get('potential_duplicates', [])
    if duplicates:
        st.markdown("#### ⚠️ Potential Duplicate Charges")
        st.caption("Similar transactions on the same day")
        
        for dup in duplicates[:5]:
            st.warning(f"**${dup['amount']:.2f}** on {dup['date']}")
            desc1 = dup['descriptions'][0]
            desc2 = dup['descriptions'][1]
            truncated_desc1 = f"{desc1[:40]}{'...' if len(desc1) > 40 else ''}"
            truncated_desc2 = f"{desc2[:40]}{'...' if len(desc2) > 40 else ''}"
            st.caption(f"Descriptions: {truncated_desc1} / {truncated_desc2}")
            st.caption(f"⚠️ {dup['warning']}")
            st.markdown("---")
    else:
        st.success("✅ No duplicate charges detected")


if __name__ == "__main__":
    render_insights_page()
