"""
Goals Management Module for CashFlow-Local

Provides business logic for financial goal tracking, progress calculation,
milestone detection, and savings projections.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal

from src.database import db_manager

logger = logging.getLogger(__name__)


# Goal type constants
GOAL_TYPES = [
    "Emergency Fund",
    "Vacation/Travel",
    "New Car/Bike",
    "Home Down Payment",
    "Education",
    "Retirement",
    "Custom"
]


def create_goal(
    name: str,
    goal_type: str,
    target_amount: float,
    target_date: date,
    priority: int = 5
) -> Optional[int]:
    """
    Create a new financial goal.
    
    Args:
        name: Goal name/description
        goal_type: Type of goal (from GOAL_TYPES)
        target_amount: Target savings amount
        target_date: Target completion date
        priority: Priority ranking (1-10, lower is higher priority)
    
    Returns:
        Goal ID if successful, None otherwise
    """
    try:
        query = """
            INSERT INTO goals (name, goal_type, target_amount, target_date, priority)
            VALUES (?, ?, ?, ?, ?)
        """
        with db_manager.get_connection() as conn:
            conn.execute(query, (name, goal_type, target_amount, target_date, priority))
            
            # Get the last inserted ID
            result = conn.execute("SELECT MAX(id) FROM goals").fetchone()
            goal_id = result[0] if result else None
            
            logger.info(f"Created goal: {name} (ID: {goal_id})")
            return goal_id
    
    except Exception as e:
        logger.error(f"Failed to create goal: {e}")
        return None


def add_contribution(goal_id: int, amount: float, contribution_date: date, notes: str = "") -> bool:
    """
    Add a contribution to a goal.
    
    Args:
        goal_id: ID of the goal
        amount: Contribution amount
        contribution_date: Date of contribution
        notes: Optional notes
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Insert contribution
        query = """
            INSERT INTO goal_contributions (goal_id, amount, contribution_date, notes)
            VALUES (?, ?, ?, ?)
        """
        with db_manager.get_connection() as conn:
            conn.execute(query, (goal_id, amount, contribution_date, notes))
            
            # Update goal current_amount
            update_query = """
                UPDATE goals 
                SET current_amount = current_amount + ?
                WHERE id = ?
            """
            conn.execute(update_query, (amount, goal_id))
            
        logger.info(f"Added contribution of {amount} to goal {goal_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to add contribution: {e}")
        return False


def get_all_goals() -> List[Dict[str, Any]]:
    """
    Retrieve all goals with calculated progress metrics.
    
    Returns:
        List of goal dictionaries with progress information
    """
    try:
        query = """
            SELECT 
                id, name, goal_type, target_amount, current_amount, 
                target_date, priority, created_at
            FROM goals
            ORDER BY priority ASC, target_date ASC
        """
        with db_manager.get_connection() as conn:
            results = conn.execute(query).fetchdf()
        
        goals = []
        for _, row in results.iterrows():
            goal = {
                'id': row['id'],
                'name': row['name'],
                'goal_type': row['goal_type'],
                'target_amount': float(row['target_amount']),
                'current_amount': float(row['current_amount']),
                'target_date': row['target_date'],
                'priority': row['priority'],
                'created_at': row['created_at']
            }
            
            # Calculate progress metrics
            goal.update(calculate_goal_metrics(goal))
            goals.append(goal)
        
        return goals
    
    except Exception as e:
        logger.error(f"Failed to retrieve goals: {e}")
        return []


def get_goal_by_id(goal_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific goal by ID.
    
    Args:
        goal_id: Goal ID
    
    Returns:
        Goal dictionary with metrics or None
    """
    try:
        query = """
            SELECT 
                id, name, goal_type, target_amount, current_amount, 
                target_date, priority, created_at
            FROM goals
            WHERE id = ?
        """
        with db_manager.get_connection() as conn:
            result = conn.execute(query, (goal_id,)).fetchone()
        
        if not result:
            return None
        
        goal = {
            'id': result[0],
            'name': result[1],
            'goal_type': result[2],
            'target_amount': float(result[3]),
            'current_amount': float(result[4]),
            'target_date': result[5],
            'priority': result[6],
            'created_at': result[7]
        }
        
        # Calculate progress metrics
        goal.update(calculate_goal_metrics(goal))
        return goal
    
    except Exception as e:
        logger.error(f"Failed to retrieve goal {goal_id}: {e}")
        return None


def calculate_goal_metrics(goal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate progress metrics for a goal.
    
    Args:
        goal: Goal dictionary
    
    Returns:
        Dictionary with calculated metrics
    """
    target_amount = goal['target_amount']
    current_amount = goal['current_amount']
    target_date = goal['target_date']
    
    # Convert string date to date object if needed
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    # Progress percentage
    progress_percent = (current_amount / target_amount * 100) if target_amount > 0 else 0
    progress_percent = min(progress_percent, 100)  # Cap at 100%
    
    # Remaining amount
    remaining_amount = max(target_amount - current_amount, 0)
    
    # Days until target
    today = date.today()
    days_remaining = (target_date - today).days
    months_remaining = max(days_remaining / 30.44, 0)  # Average days per month
    
    # Required monthly savings
    required_monthly = 0
    if months_remaining > 0 and remaining_amount > 0:
        required_monthly = remaining_amount / months_remaining
    
    # Current milestone
    milestone = get_milestone(progress_percent)
    
    # Is on track?
    days_total = (target_date - goal['created_at'].date()).days if isinstance(goal['created_at'], datetime) else 365
    expected_progress = ((days_total - days_remaining) / days_total * 100) if days_total > 0 else 0
    is_on_track = progress_percent >= expected_progress or progress_percent >= 100
    
    # Projected completion date
    projected_date = None
    if current_amount > 0 and remaining_amount > 0:
        days_elapsed = (today - goal['created_at'].date()).days if isinstance(goal['created_at'], datetime) else 1
        if days_elapsed > 0:
            daily_rate = current_amount / days_elapsed
            if daily_rate > 0:
                days_to_completion = remaining_amount / daily_rate
                projected_date = today + timedelta(days=int(days_to_completion))
    
    return {
        'progress_percent': round(progress_percent, 2),
        'remaining_amount': remaining_amount,
        'days_remaining': days_remaining,
        'months_remaining': round(months_remaining, 1),
        'required_monthly': round(required_monthly, 2),
        'milestone': milestone,
        'is_on_track': is_on_track,
        'projected_date': projected_date
    }


def get_milestone(progress_percent: float) -> str:
    """
    Get the current milestone based on progress percentage.
    
    Args:
        progress_percent: Progress percentage
    
    Returns:
        Milestone description
    """
    if progress_percent >= 100:
        return "🎉 Completed"
    elif progress_percent >= 75:
        return "🎯 75% Milestone"
    elif progress_percent >= 50:
        return "🎯 50% Milestone"
    elif progress_percent >= 25:
        return "🎯 25% Milestone"
    else:
        return "🚀 Getting Started"


def get_goal_contributions(goal_id: int) -> List[Dict[str, Any]]:
    """
    Get all contributions for a specific goal.
    
    Args:
        goal_id: Goal ID
    
    Returns:
        List of contribution dictionaries
    """
    try:
        query = """
            SELECT id, goal_id, amount, contribution_date, notes, created_at
            FROM goal_contributions
            WHERE goal_id = ?
            ORDER BY contribution_date DESC
        """
        with db_manager.get_connection() as conn:
            results = conn.execute(query, (goal_id,)).fetchdf()
        
        return results.to_dict('records') if not results.empty else []
    
    except Exception as e:
        logger.error(f"Failed to retrieve contributions for goal {goal_id}: {e}")
        return []


def update_goal(
    goal_id: int,
    name: Optional[str] = None,
    target_amount: Optional[float] = None,
    target_date: Optional[date] = None,
    priority: Optional[int] = None
) -> bool:
    """
    Update goal details.
    
    Args:
        goal_id: Goal ID
        name: New name (optional)
        target_amount: New target amount (optional)
        target_date: New target date (optional)
        priority: New priority (optional)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if target_amount is not None:
            updates.append("target_amount = ?")
            params.append(target_amount)
        if target_date is not None:
            updates.append("target_date = ?")
            params.append(target_date)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        
        if not updates:
            return False
        
        query = f"UPDATE goals SET {', '.join(updates)} WHERE id = ?"
        params.append(goal_id)
        
        with db_manager.get_connection() as conn:
            conn.execute(query, params)
        
        logger.info(f"Updated goal {goal_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to update goal {goal_id}: {e}")
        return False


def delete_goal(goal_id: int) -> bool:
    """
    Delete a goal and its contributions.
    
    Args:
        goal_id: Goal ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db_manager.get_connection() as conn:
            # Delete contributions first
            conn.execute("DELETE FROM goal_contributions WHERE goal_id = ?", (goal_id,))
            # Delete goal
            conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        
        logger.info(f"Deleted goal {goal_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to delete goal {goal_id}: {e}")
        return False


def get_top_goals(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get top priority goals.
    
    Args:
        limit: Number of goals to return
    
    Returns:
        List of top priority goals
    """
    all_goals = get_all_goals()
    return all_goals[:limit]


from datetime import timedelta
