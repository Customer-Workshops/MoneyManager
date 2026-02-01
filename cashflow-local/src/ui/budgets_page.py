"""
Budgets Page for CashFlow-Local Streamlit App

Allows users to set and manage monthly budget limits per category.
"""

import streamlit as st
import pandas as pd
import logging

from src.database import db_manager
from src.categorization import category_engine

logger = logging.getLogger(__name__)


def render_budgets_page():
    """
    Render the budgets management page.
    
    Features:
    - View existing budgets
    - Add new category budgets
    - Edit budget limits
    - Delete budgets
    """
    st.header("💰 Budget Management")
    st.markdown("""
    Set monthly spending limits for each category. 
    The dashboard will highlight categories that exceed their budget in red.
    """)
    
    # Fetch existing budgets
    try:
        query = "SELECT id, category, monthly_limit FROM budgets ORDER BY category"
        results = db_manager.execute_query(query)
        
        if results:
            # Display existing budgets
            st.subheader("Current Budgets")
            
            df = pd.DataFrame(results, columns=['id', 'category', 'monthly_limit'])
            df['monthly_limit'] = df['monthly_limit'].apply(lambda x: f"${x:,.2f}")
            
            # Editable table
            edited_df = st.data_editor(
                df,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "category": st.column_config.TextColumn("Category", disabled=True),
                    "monthly_limit": st.column_config.TextColumn("Monthly Limit")
                },
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                key="budget_editor"
            )
            
            # Delete budget
            st.divider()
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🗑️ Delete Selected", type="secondary"):
                    # For simplicity, we'll add a selectbox to choose which to delete
                    st.info("Use the 'Add New Budget' section to manage budgets")
        
        else:
            st.info("No budgets configured yet. Add your first budget below!")
        
        # Add new budget
        st.divider()
        st.subheader("Add New Budget")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Get available categories
            all_categories = category_engine.get_all_categories()
            
            # Remove categories that already have budgets
            existing_categories = [row[1] for row in results] if results else []
            available_categories = [cat for cat in all_categories if cat not in existing_categories and cat != "Uncategorized"]
            
            if not available_categories:
                st.warning("All categories already have budgets!")
                new_category = None
            else:
                new_category = st.selectbox("Category", options=available_categories)
        
        with col2:
            new_limit = st.number_input(
                "Monthly Limit ($)",
                min_value=0.0,
                value=100.0,
                step=10.0,
                format="%.2f"
            )
        
        with col3:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("➕ Add Budget", type="primary", disabled=not new_category):
                try:
                    # Insert new budget
                    insert_query = """
                        INSERT INTO budgets (category, monthly_limit)
                        VALUES (?, ?)
                    """
                    with db_manager.get_connection() as conn:
                        conn.execute(insert_query, (new_category, new_limit))
                    
                    st.success(f"✅ Added budget for {new_category}: ${new_limit:,.2f}/month")
                    st.rerun()
                
                except Exception as e:
                    logger.error(f"Failed to add budget: {e}")
                    st.error(f"Failed to add budget: {str(e)}")
        
        # Quick actions
        st.divider()
        st.subheader("Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Reset All Budgets", type="secondary"):
                if st.session_state.get('confirm_reset', False):
                    try:
                        with db_manager.get_connection() as conn:
                            conn.execute("DELETE FROM budgets")
                        st.success("All budgets deleted!")
                        st.session_state['confirm_reset'] = False
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Failed to reset budgets: {e}")
                        st.error(f"Failed to reset budgets: {str(e)}")
                else:
                    st.session_state['confirm_reset'] = True
                    st.warning("⚠️ Click again to confirm deletion of all budgets")
        
        with col2:
            if st.button("📋 View Budget Template"):
                st.info("""
                **Suggested Monthly Budgets:**
                - Groceries: $400
                - Dining: $200
                - Transportation: $150
                - Entertainment: $100
                - Shopping: $200
                - Coffee: $50
                """)
    
    except Exception as e:
        logger.error(f"Failed to load budgets page: {e}")
        st.error(f"Failed to load budgets: {str(e)}")
