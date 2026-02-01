"""
Search utilities for advanced transaction filtering.

Provides fuzzy search, regex support, and search optimization.
"""

import re
import logging
from typing import List, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def fuzzy_match(text: str, pattern: str, threshold: float = 0.6) -> bool:
    """
    Perform fuzzy matching between text and pattern.
    
    Uses SequenceMatcher for similarity scoring to handle typos.
    
    Args:
        text: Text to search in
        pattern: Pattern to search for
        threshold: Similarity threshold (0.0 to 1.0)
    
    Returns:
        True if similarity exceeds threshold
    
    Example:
        fuzzy_match("Starbucks", "Starbuck", 0.8) -> True
        fuzzy_match("Amazon", "Amzon", 0.8) -> True
    """
    if not pattern:
        return True
    
    text_lower = text.lower()
    pattern_lower = pattern.lower()
    
    # Exact substring match always passes
    if pattern_lower in text_lower:
        return True
    
    # Calculate similarity ratio
    similarity = SequenceMatcher(None, text_lower, pattern_lower).ratio()
    
    return similarity >= threshold


def regex_search(text: str, pattern: str) -> bool:
    """
    Perform regex search on text.
    
    Args:
        text: Text to search in
        pattern: Regex pattern
    
    Returns:
        True if pattern matches text
    
    Example:
        regex_search("Amount: $123.45", r"\\$\\d+\\.\\d+") -> True
    """
    try:
        return bool(re.search(pattern, text, re.IGNORECASE))
    except re.error as e:
        logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        # Fallback to substring search
        return pattern.lower() in text.lower()


def build_search_query(
    base_query: str,
    search_text: str,
    use_fuzzy: bool = False,
    use_regex: bool = False
) -> tuple[str, str]:
    """
    Build SQL query for search with fuzzy or regex support.
    
    Args:
        base_query: Base SQL query
        search_text: Search text
        use_fuzzy: Enable fuzzy matching (done in Python, not SQL)
        use_regex: Enable regex matching (done in Python, not SQL)
    
    Returns:
        Tuple of (query, search_mode)
        - query: Modified SQL query
        - search_mode: 'exact', 'fuzzy', or 'regex'
    
    Note:
        Fuzzy and regex searches require post-processing in Python
        as DuckDB has limited support for these features.
    """
    if use_regex:
        # Regex search - we'll do post-processing
        return base_query, 'regex'
    elif use_fuzzy:
        # Fuzzy search - we'll do post-processing
        return base_query, 'fuzzy'
    else:
        # Standard SQL LIKE search
        return base_query, 'exact'


def filter_by_search(
    transactions: List[dict],
    search_text: str,
    search_mode: str = 'exact',
    fuzzy_threshold: float = 0.6
) -> List[dict]:
    """
    Filter transactions list by search text with different modes.
    
    Args:
        transactions: List of transaction dictionaries
        search_text: Search text
        search_mode: 'exact', 'fuzzy', or 'regex'
        fuzzy_threshold: Similarity threshold for fuzzy search
    
    Returns:
        Filtered list of transactions
    """
    if not search_text or not transactions:
        return transactions
    
    filtered = []
    
    for txn in transactions:
        description = txn.get('description', '')
        
        if search_mode == 'fuzzy':
            if fuzzy_match(description, search_text, fuzzy_threshold):
                filtered.append(txn)
        elif search_mode == 'regex':
            if regex_search(description, search_text):
                filtered.append(txn)
        else:  # exact
            if search_text.lower() in description.lower():
                filtered.append(txn)
    
    return filtered
