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
