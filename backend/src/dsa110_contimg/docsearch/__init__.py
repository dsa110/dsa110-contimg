# backend/src/dsa110_contimg/docsearch/__init__.py

"""
Documentation search module (SQLite-based vector search).

Provides:
- DocSearch: SQLite-backed semantic search over documentation
- SearchResult: Search result dataclass
"""

from .search import DocSearch, SearchResult

__all__ = ["DocSearch", "SearchResult"]
