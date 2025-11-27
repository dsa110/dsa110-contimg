# Local Documentation Search

Fully local, service-free documentation search using SQLite and vector
embeddings.

## Overview

This module provides semantic search over documentation without requiring any
external services to run. It uses:

- **OpenAI embeddings** (text-embedding-3-small) for semantic understanding
- **sqlite-vec** for efficient vector similarity search
- **Local caching** to minimize API calls

## Quick Start

### 1. Index Documentation

```bash
conda activate casa6

# Index the docs directory
python -m dsa110_contimg.docsearch.cli index

# Force re-index everything
python -m dsa110_contimg.docsearch.cli index --force
```

### 2. Search

```bash
# Search from command line
python -m dsa110_contimg.docsearch.cli search "how to convert UVH5 files"

# More results
python -m dsa110_contimg.docsearch.cli search "calibration" --top-k 10
```

### 3. Python API

```python
from dsa110_contimg.docsearch import DocSearch

# Initialize (uses OPENAI_API_KEY from environment)
search = DocSearch()

# Search
results = search.search("How do I run the imaging pipeline?", top_k=5)

for r in results:
    print(f"Score: {r.score:.3f}")
    print(f"File: {r.file_path}")
    print(f"Section: {r.heading}")
    print(f"Content: {r.content[:200]}...")
    print()

# Index new files
search.index_file("/path/to/new/doc.md")

# Re-index directory (only changed files)
search.index_directory("/data/dsa110-contimg/docs")

# Get stats
print(search.get_stats())
```

## CLI Commands

| Command  | Description               |
| -------- | ------------------------- |
| `index`  | Index documentation files |
| `search` | Search indexed content    |
| `stats`  | Show index statistics     |
| `clear`  | Clear the index           |

### Index Options

```bash
python -m dsa110_contimg.docsearch.cli index \
    --docs-dir /path/to/docs \
    --extensions ".md,.txt,.rst" \
    --force  # Re-index all files
```

### Search Options

```bash
python -m dsa110_contimg.docsearch.cli search "query" \
    --top-k 5 \
    --min-score 0.3 \
    --full  # Show full content
```

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    DocSearch                                 │
├─────────────────────────────────────────────────────────────┤
│  search.py      - Main search interface                     │
│  embedder.py    - OpenAI embedding generation + caching     │
│  chunker.py     - Document chunking with overlap            │
│  cli.py         - Command-line interface                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite Databases                          │
├─────────────────────────────────────────────────────────────┤
│  state/docsearch.sqlite3       - Chunks + vector index      │
│  state/embedding_cache.sqlite3 - Cached embeddings          │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Incremental Updates

Only changed files are re-indexed:

```python
# This only processes new/modified files
search.index_directory("/data/dsa110-contimg/docs")

# Force re-index everything
search.index_directory("/data/dsa110-contimg/docs", force=True)
```

### Embedding Cache

Embeddings are cached locally to minimize OpenAI API calls:

```python
>>> search.embedder.get_cache_stats()
{
    'total_cached': 5000,
    'by_model': {'text-embedding-3-small': 5000},
    'cache_db': '/data/dsa110-contimg/state/embedding_cache.sqlite3'
}
```

### Heading-Aware Chunking

Documents are split at markdown headings to preserve context:

```python
from dsa110_contimg.docsearch import chunk_document

chunks = chunk_document(
    content="# Title\n\nContent...",
    file_path="doc.md",
    chunk_size=512,      # Target tokens per chunk
    chunk_overlap=64,    # Overlap between chunks
)

for c in chunks:
    print(f"{c.heading}: {c.start_line}-{c.end_line}")
```

## Configuration

### Environment Variables

| Variable         | Description                   | Default  |
| ---------------- | ----------------------------- | -------- |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Required |

### Database Locations

| Database        | Path                            | Purpose           |
| --------------- | ------------------------------- | ----------------- |
| Search Index    | `state/docsearch.sqlite3`       | Chunks + vectors  |
| Embedding Cache | `state/embedding_cache.sqlite3` | Cached embeddings |

## Comparison with RAGFlow

| Feature           | DocSearch     | RAGFlow            |
| ----------------- | ------------- | ------------------ |
| External services | None          | Docker containers  |
| Setup complexity  | `pip install` | Docker compose     |
| Embedding source  | OpenAI API    | Configurable       |
| Storage           | SQLite        | PostgreSQL + MinIO |
| Chat interface    | No            | Yes                |
| MCP support       | No            | Custom server      |

**Use DocSearch when:**

- You want zero external dependencies
- You only need search (not chat)
- You're already calling OpenAI APIs

**Use RAGFlow when:**

- You want a full RAG chat experience
- You need GraphRAG or RAPTOR features
- You want a web UI for document management
