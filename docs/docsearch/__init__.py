"""
Local documentation search using SQLite and vector embeddings.

**LOCATION:** This module has been moved to `docs/docsearch/` and is provided as
reference code and standalone tools. It is no longer part of the `dsa110_contimg`
Python package.

This module provides a fully local, service-free documentation search
using SQLite with the sqlite-vec extension for vector similarity search.

Features:
- No external services required (embeddings cached locally)
- Fast similarity search using sqlite-vec
- Automatic chunking and embedding of markdown/text files
- Incremental updates (only re-embed changed files)

Usage:
    # Navigate to the directory
    cd /data/dsa110-contimg/docs/docsearch
    
    # Index documentation (one-time or on updates)
    python cli.py index
    
    # Search
    python cli.py search "How do I convert UVH5 to MS?"
    
    # Show stats
    python cli.py stats

Configuration:
    Set OPENAI_API_KEY environment variable for embeddings.
    Database stored at: /data/dsa110-contimg/state/db/docsearch.sqlite3
"""

try:
    from search import DocSearch
    from embedder import Embedder
    from chunker import chunk_document
    
    __all__ = [
        "DocSearch",
        "Embedder", 
        "chunk_document",
    ]
except ImportError:
    # Expected - this is now reference code
    __all__ = []
