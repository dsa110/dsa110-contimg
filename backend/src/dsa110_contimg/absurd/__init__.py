"""
Absurd durable task queue integration for DSA-110 pipeline.

This package provides integration with the Absurd workflow manager
for durable, fault-tolerant task execution.
"""

from .client import AbsurdClient
from .config import AbsurdConfig

__all__ = ["AbsurdClient", "AbsurdConfig"]
