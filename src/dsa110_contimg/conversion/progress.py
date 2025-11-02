"""
Progress reporting utilities for conversion operations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProgressStep:
    """Single progress step."""
    timestamp: float
    message: str
    status: str  # "info", "success", "warning", "error"


class ProgressReporter:
    """Progress reporting for long operations."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.steps: List[ProgressStep] = []
    
    def step(self, message: str, status: str = "info") -> None:
        """Report a workflow step."""
        timestamp = time.time()
        step = ProgressStep(timestamp=timestamp, message=message, status=status)
        self.steps.append(step)
        
        if self.verbose:
            status_symbol = {
                "info": "ℹ",
                "success": "✓",
                "warning": "⚠",
                "error": "✗"
            }.get(status, "•")
            print(f"{status_symbol} {message}")
    
    def info(self, message: str) -> None:
        """Report info step."""
        self.step(message, "info")
    
    def success(self, message: str) -> None:
        """Report success step."""
        self.step(message, "success")
    
    def warning(self, message: str) -> None:
        """Report warning step."""
        self.step(message, "warning")
    
    def error(self, message: str) -> None:
        """Report error step."""
        self.step(message, "error")
    
    def get_summary(self) -> dict:
        """Get summary of all steps."""
        if not self.steps:
            return {"total_steps": 0, "steps": []}
        
        total_time = self.steps[-1].timestamp - self.steps[0].timestamp
        
        return {
            "total_steps": len(self.steps),
            "total_time_seconds": total_time,
            "steps": [
                {
                    "timestamp": s.timestamp,
                    "message": s.message,
                    "status": s.status
                }
                for s in self.steps
            ]
        }

