# Local Documentation Search (docsearch)

Local, service-free documentation search using SQLite and vector embeddings.

## Overview

The `docsearch` module provides semantic search over documentation without
requiring any external services to run. It uses:

- **OpenAI embeddings** (`text-embedding-3-small`) for semantic understanding
- **sqlite-vec** for efficient vector similarity search
- **Local caching** to minimize API calls

This is an alternative to RAGFlow that requires no Docker containers or
background services - just Python and an OpenAI API key.

> Location: DocSearch now lives in `docs/docsearch/` as standalone reference
> code. It is **not** part of the `dsa110_contimg` Python package; run it from
> that directory or add it to `PYTHONPATH` when importing.

## Quick Start

### Index Documentation

```bash
conda activate casa6
cd /data/dsa110-contimg/docs/docsearch

# Index the docs directory (run once, then incrementally)
python cli.py index

# Force re-index everything
python cli.py index --force
```

### Search from Command Line

```bash
# Basic search
cd /data/dsa110-contimg/docs/docsearch
python cli.py search "how to convert UVH5 files"

# More results with lower threshold
python cli.py search "calibration" --top-k 10 --min-score 0.2
```

### Python API

```python
import sys
sys.path.insert(0, "/data/dsa110-contimg/docs/docsearch")  # add local module directory

from search import DocSearch

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
stats = search.index_directory("/data/dsa110-contimg/docs")
print(f"Indexed {stats['chunks_indexed']} chunks from {stats['files_processed']} files")
```

## CLI Reference

### `index` - Index Documentation

```bash
cd /data/dsa110-contimg/docs/docsearch
python cli.py index [OPTIONS]
```

| Option         | Default                     | Description                          |
| -------------- | --------------------------- | ------------------------------------ |
| `--docs-dir`   | `/data/dsa110-contimg/docs` | Directory to index                   |
| `--extensions` | `.md,.txt,.rst`             | File extensions (comma-separated)    |
| `--force`      | `false`                     | Re-index all files even if unchanged |

### `search` - Search Documents

```bash
cd /data/dsa110-contimg/docs/docsearch
python cli.py search QUERY [OPTIONS]
```

| Option        | Default | Description                        |
| ------------- | ------- | ---------------------------------- |
| `--top-k`     | `5`     | Number of results to return        |
| `--min-score` | `0.3`   | Minimum similarity score (0-1)     |
| `--full`      | `false` | Show full content (don't truncate) |

### `stats` - Show Statistics

```bash
cd /data/dsa110-contimg/docs/docsearch
python cli.py stats
```

### `clear` - Clear Index

```bash
cd /data/dsa110-contimg/docs/docsearch
python cli.py clear [-y]
```

## API Reference

### `DocSearch`

Main search interface.

```python
class DocSearch:
    def __init__(
        self,
        db_path: Path = None,      # Default: state/docsearch.sqlite3
        embedder: Embedder = None,  # Default: creates new Embedder
    ): ...

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]: ...

    def index_file(
        self,
        path: Path,
        content: str = None,
        force: bool = False,
    ) -> int: ...  # Returns number of chunks indexed

    def index_directory(
        self,
        directory: Path,
        extensions: tuple[str, ...] = (".md", ".txt", ".rst"),
        exclude_patterns: tuple[str, ...] = ("__pycache__", ".git", "node_modules", "site"),
        force: bool = False,
    ) -> dict: ...  # Returns stats

    def get_stats(self) -> dict: ...
    def clear(self) -> None: ...
```

### `SearchResult`

```python
@dataclass
class SearchResult:
    content: str      # Chunk content
    file_path: str    # Source file
    start_line: int   # Start line in file
    end_line: int     # End line in file
    heading: str      # Nearest markdown heading
    score: float      # Similarity score (0-1)
```

### `Embedder`

Embedding generation with caching.

```python
class Embedder:
    def __init__(
        self,
        api_key: str = None,  # Default: OPENAI_API_KEY env var
        model: str = "text-embedding-3-small",
        cache_db: Path = None,  # Default: state/embedding_cache.sqlite3
    ): ...

    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]: ...
    def get_cache_stats(self) -> dict: ...
```

## Database Schema

### `state/docsearch.sqlite3`

```sql
-- Document chunks
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    heading TEXT,
    created_at TIMESTAMP
);

-- Vector embeddings (sqlite-vec virtual table)
CREATE VIRTUAL TABLE chunk_embeddings USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[1536]
);

-- File tracking for incremental updates
CREATE TABLE indexed_files (
    file_path TEXT PRIMARY KEY,
    file_hash TEXT NOT NULL,
    indexed_at TIMESTAMP
);
```

### `state/embedding_cache.sqlite3`

```sql
CREATE TABLE embedding_cache (
    text_hash TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    embedding BLOB NOT NULL,
    created_at TIMESTAMP
);
```

## Comparison with RAGFlow

| Feature           | DocSearch     | RAGFlow                 |
| ----------------- | ------------- | ----------------------- |
| External services | None          | Docker containers       |
| Setup             | Local scripts (`docs/docsearch`) | Docker Compose          |
| Embedding source  | OpenAI API    | Configurable            |
| Storage           | SQLite        | PostgreSQL + MinIO      |
| Chat interface    | No            | Yes (+ simple `ask()`)  |
| GraphRAG/RAPTOR   | No            | Yes                     |
| MCP server        | No            | Custom server available |

**Use DocSearch when:**

- You want zero external dependencies
- You only need search (not chat)
- You're already calling OpenAI APIs
- You want simple, maintainable code

**Use RAGFlow when:**

- You want a full RAG chat experience
- You need GraphRAG or RAPTOR features
- You want a web UI for document management
- You need synthesis across multiple documents

**RAGFlow Quick Usage:**

```python
import sys
sys.path.insert(0, "/data/dsa110-contimg/docs/ragflow")  # add standalone module

from client import RAGFlowClient

client = RAGFlowClient()  # Uses RAGFLOW_API_KEY env var
answer = client.ask("What error detection protections are implemented?")
print(answer)
```

## See Also

- [RAGFlow Integration](../../docsearch/../ragflow/README.md) - Full RAG system
  with chat
- [MCP Server](../../ragflow/README.md#mcp-server-integration) - Agent tool
  integration
