"""
Database transaction coordinator for multi-database operations.
Provides coordination for operations that span multiple SQLite databases.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for a database."""

    name: str
    path: Path


class DatabaseCoordinator:
    """Coordinates transactions across multiple SQLite databases."""

    def __init__(self, databases: List[DatabaseConfig]):
        self.databases = {db.name: db for db in databases}
        self.connections: Dict[str, sqlite3.Connection] = {}

    @contextmanager
    def transaction(self, db_names: List[str]):
        """Context manager for coordinated transactions across databases."""
        connections = []
        try:
            # Begin transactions on all databases
            for db_name in db_names:
                if db_name not in self.databases:
                    raise ValueError(f"Database {db_name} not found")

                db_config = self.databases[db_name]
                conn = sqlite3.connect(str(db_config.path))
                conn.execute("BEGIN TRANSACTION")
                connections.append((db_name, conn))

            yield connections

            # Commit all transactions
            for db_name, conn in connections:
                conn.commit()
                conn.close()

        except Exception as e:
            # Rollback all transactions on error
            logger.error(f"Transaction failed, rolling back: {e}")
            for db_name, conn in connections:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            raise

    def health_check(self) -> Dict[str, str]:
        """Check health of all databases."""
        health = {}
        for db_name, db_config in self.databases.items():
            try:
                conn = sqlite3.connect(str(db_config.path))
                conn.execute("SELECT 1").fetchone()
                conn.close()
                health[db_name] = "healthy"
            except Exception as e:
                health[db_name] = f"error: {str(e)}"
        return health
