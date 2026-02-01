"""
Shared utility functions for UI components.
"""

from typing import List


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


def get_categories_by_type(transaction_type: str) -> List[str]:
    """
    Get categories filtered by transaction type.
    
    Args:
        transaction_type: '💸 Expense', '💰 Income', or '🔄 Transfer'
    
    Returns:
        List of category names with icons
    """
    # Define category mappings
    expense_categories = [
        "🍔 Food & Dining",
        "🚗 Transport",
        "🏠 Housing",
        "💡 Utilities",
        "🛒 Shopping",
        "🎬 Entertainment",
        "💊 Healthcare",
        "✏️ Education",
        "🎁 Gifts & Donations",
        "💼 Business Expenses"
    ]
    
    income_categories = [
        "💼 Salary",
        "💵 Freelance",
        "📈 Investment Returns",
        "🎁 Gifts Received",
        "↩️ Refunds"
    ]
    
    transfer_categories = [
        "🏦 Account Transfer",
        "💳 Credit Card Payment",
        "💰 Savings Deposit"
    ]
    
    if "Expense" in transaction_type:
        return expense_categories
    elif "Income" in transaction_type:
        return income_categories
    else:
        return transfer_categories
