"""
Writer strategies for DSA-110 UVH5 to MS conversion.

This module provides a Strategy pattern implementation for different
MS writing approaches.
"""

from .base import MSWriter
from .direct_subband import DirectSubbandWriter
from .pyuvdata_monolithic import PyuvdataMonolithicWriter


def get_writer(strategy: str) -> type:
    """Get a writer strategy class by name.

    Args:
        strategy: Name of the strategy ('pyuvdata' or 'direct-subband')

    Returns:
        MSWriter class

    Raises:
        ValueError: If strategy is not recognized
    """
    strategies = {
        'pyuvdata': PyuvdataMonolithicWriter,
        'direct-subband': DirectSubbandWriter,
    }

    if strategy not in strategies:
        raise ValueError(
            f"Unknown writer strategy: {strategy}. Available: {list(strategies.keys())}")

    return strategies[strategy]
