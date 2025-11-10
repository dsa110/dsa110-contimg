"""
Writer strategies for DSA-110 UVH5 to MS conversion.

This module provides a Strategy pattern implementation for different
MS writing approaches.

Production use: Always use 'parallel-subband' (or 'direct-subband' alias).
Testing use: 'pyuvdata' is available for testing scenarios with ≤2 subbands.
"""

from .base import MSWriter
from .direct_subband import DirectSubbandWriter
from .pyuvdata_monolithic import PyuvdataMonolithicWriter


def get_writer(strategy: str) -> type:
    """Get a writer strategy class by name.

    Production processing always uses 16 subbands and should use 'parallel-subband'.
    The 'pyuvdata' writer is available for testing scenarios with ≤2 subbands only.

    Args:
        strategy: Name of the strategy:
            - 'parallel-subband': Production writer (default for 16 subbands)
            - 'direct-subband': Alias for 'parallel-subband' (backward compatibility)
            - 'pyuvdata': Testing-only writer (for ≤2 subbands)

    Returns:
        MSWriter class

    Raises:
        ValueError: If strategy is not recognized
    """
    strategies = {
        "pyuvdata": PyuvdataMonolithicWriter,  # Testing only: ≤2 subbands
        "parallel-subband": DirectSubbandWriter,  # Production: 16 subbands
        "direct-subband": DirectSubbandWriter,  # Backward compatibility alias
    }

    if strategy not in strategies:
        raise ValueError(
            f"Unknown writer strategy: {strategy}. Available: {list(strategies.keys())}"
        )

    return strategies[strategy]
