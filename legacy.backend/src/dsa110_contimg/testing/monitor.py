"""
Minimal test monitor stubs to satisfy imports in legacy scripts/tests.

These are lightweight implementations intended for test collection only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SuiteRun:
    """Minimal suite run representation."""

    passed: int
    failed: int
    errors: int
    total_tests: int
    commit_hash: str = ""
    branch: str = ""


class TestMonitor:
    """Stubbed test monitor for import compatibility."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def record_suite_run(self, suite_run: SuiteRun) -> int:
        """Pretend to record a suite run and return a run id."""
        return 1

    def get_regression_analysis(self) -> Dict[str, Any]:
        """Return a stable regression analysis placeholder."""
        return {
            "stable": True,
            "regressions": [],  # type: List[Dict[str, Any]]
            "improvements": [],  # type: List[Dict[str, Any]]
            "total_runs": 1,
        }


def run_comprehensive_tests() -> SuiteRun:
    """Return a dummy suite result."""
    return SuiteRun(passed=0, failed=0, errors=0, total_tests=0)
