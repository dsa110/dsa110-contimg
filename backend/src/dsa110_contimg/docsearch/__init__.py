# backend/src/dsa110_contimg/docsearch/__init__.py

"""
Documentation search module (SQLite-based vector search).

The actual implementation lives in docs/docsearch/ and provides:
- DocSearch: SQLite-backed semantic search over documentation
- SearchResult: Search result dataclass
"""

import sys
from pathlib import Path

# Import from docs/docsearch/ which contains the actual implementation
docs_docsearch = Path(__file__).resolve().parents[3] / "docs" / "docsearch"
if str(docs_docsearch) not in sys.path:
    sys.path.insert(0, str(docs_docsearch))

from search import DocSearch, SearchResult

__all__ = ["DocSearch", "SearchResult"]