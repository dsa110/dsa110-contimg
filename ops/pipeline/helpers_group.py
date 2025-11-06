"""
Shared group ID parsing helpers for ops pipeline scripts.

This module consolidates duplicate group ID parsing functions.
"""

import os


def group_id_from_path(path: str) -> str:
    """
    Extract group ID from file path.
    
    Group ID is the base filename without the subband suffix (e.g., _sb00).
    
    Args:
        path: File path (e.g., "/path/to/group_sb00.hdf5")
    
    Returns:
        Group ID (e.g., "group")
    
    Example:
        >>> group_id_from_path("/data/0834_555_sb00.hdf5")
        '0834_555'
    """
    base = os.path.basename(path)
    return base.split('_sb', 1)[0]

