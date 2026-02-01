"""
Shared utility functions for UI components.
"""


def get_type_icon(transaction_type: str) -> str:
    """
    Get emoji icon for transaction type.
    
    Args:
        transaction_type: 'Debit', 'Credit', or 'Transfer'
    
    Returns:
        Emoji icon string
    """
    icons = {
        'Debit': '💸',     # Expense - outgoing transactions
        'Credit': '💰',    # Income - incoming transactions
        'Transfer': '🔄'   # Transfer - internal transfers
    }
    return icons.get(transaction_type, '💳')


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
