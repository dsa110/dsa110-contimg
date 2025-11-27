"""
Local documentation search using SQLite and vector embeddings.

This module provides a fully local, service-free documentation search
using SQLite with the sqlite-vec extension for vector similarity search.

Features:
- No external services required (embeddings cached locally)
- Fast similarity search using sqlite-vec
- Automatic chunking and embedding of markdown/text files
- Incremental updates (only re-embed changed files)

Example:
    >>> from dsa110_contimg.docsearch import DocSearch
    >>> search = DocSearch()
    >>> 
    >>> # Index documentation (one-time or on updates)
    >>> search.index_directory("/data/dsa110-contimg/docs")
    >>> 
    >>> # Search
    >>> results = search.search("How do I convert UVH5 to MS?")
    >>> for r in results:
    ...     print(f"{r['score']:.3f} - {r['file']}: {r['content'][:100]}...")

Configuration:
    Set OPENAI_API_KEY environment variable for embeddings.
    Database stored at: /data/dsa110-contimg/state/docsearch.sqlite3
"""

from .search import DocSearch
from .embedder import Embedder
from .chunker import chunk_document

__all__ = [
    "DocSearch",
    "Embedder", 
    "chunk_document",
]
