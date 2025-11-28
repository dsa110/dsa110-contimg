# RAGFlow Integration - Reference Implementation

> **IMPORTANT:** This directory contains **reference code and examples only**.
> These files have been moved from `backend/src/dsa110_contimg/ragflow/` to
> `docs/ragflow/` and are **no longer part of the Python package**.

## Location Change

- **Old location:** `backend/src/dsa110_contimg/ragflow/` (removed)
- **New location:** `docs/ragflow/` (reference/examples)
- **Import path:** No longer available - use standalone scripts

## Overview

This directory provides reference implementations for integrating with
[RAGFlow](https://ragflow.io/) for documentation retrieval using RAG
(Retrieval-Augmented Generation).

**Recommended Alternative:** For lightweight documentation search, use
`DocSearch` in `docs/docsearch/` instead. RAGFlow is optional and intended for
advanced use cases requiring full RAG capabilities.

**Location & usage:** Lives in `docs/ragflow/` as standalone reference code
(not installed as `dsa110_contimg.ragflow`). Prefer the REST API via the CLI
and `client.py`. The old MCP server is archived (`mcp_server_dormant.py`) and
should not be used.

RAGFlow provides:

- **Document indexing** for DSA-110 documentation
- **Semantic search** with embedding-based retrieval
- **REST API** for search/chat (preferred entry point)

## Quick Start

### 1. Set Up API Key

First, deploy RAGFlow (see `docs/ops/ragflow/README.md`), then create an API
key:

1. Open http://localhost:9080 in your browser
2. Register or log in
3. Go to **Settings** → **API Keys**
4. Create a new API key
5. Export the key:

```bash
export RAGFLOW_API_KEY="ragflow-xxxxxxxxxxxxxxxxxxxxx"
```

### 2. Upload Documentation

Upload the DSA-110 documentation using the standalone script:

```bash
conda activate casa6
cd /data/dsa110-contimg/docs/ragflow

# Upload all docs with default settings
python cli.py upload --api-key $RAGFLOW_API_KEY

# Or upload a specific directory
python cli.py upload \
    --docs-dir /data/dsa110-contimg/docs \
    --dataset "DSA-110 Documentation" \
    --api-key $RAGFLOW_API_KEY
```

### 3. Query the Knowledge Base

```bash
cd /data/dsa110-contimg/docs/ragflow
# Search for information
python cli.py query \
    "How do I convert UVH5 files to Measurement Sets?" \
    --api-key $RAGFLOW_API_KEY
```

### 4. Use from Python (Advanced)

Since this is reference code, you can import locally if needed:

```python
import sys
sys.path.insert(0, '/data/dsa110-contimg/docs/ragflow')
from client import RAGFlowClient

client = RAGFlowClient()  # Uses RAGFLOW_API_KEY env var

# Simple Q&A - easiest method
answer = client.ask("How do I convert UVH5 files to Measurement Sets?")
print(answer)

# Search documents (raw retrieval)
results = client.retrieve(
    dataset_ids=["dataset-id"],
    question="How do I run the calibration pipeline?",
)

for chunk in results:
    print(f"Score: {chunk['similarity']:.4f}")
    print(chunk["content"][:200])
```

**Note:** All code here calls the RAGFlow REST API (default
`http://localhost:9380`). For agents, prefer hitting the REST API directly
instead of the archived MCP server.

## CLI Commands

All commands should be run from the `docs/ragflow/` directory:

```bash
cd /data/dsa110-contimg/docs/ragflow
```

### Upload Documents

```bash
python cli.py upload [OPTIONS]

Options:
  --docs-dir PATH      Documentation directory (default: /data/dsa110-contimg/docs)
  --dataset NAME       Dataset name (default: "DSA-110 Documentation")
  --description TEXT   Dataset description
  --chunk-method TEXT  Chunking method: naive, markdown, paper, book, qa, table
  --batch-size INT     Files per upload batch (default: 10)
  --no-recursive       Don't scan subdirectories
  --no-parse          Don't parse documents after upload
  --no-wait           Don't wait for parsing to complete
```

### List Datasets

```bash
python cli.py list-datasets
```

### List Documents

```bash
python cli.py list-documents "DSA-110 Documentation"
```

### Query

```bash
python cli.py query "your question" [OPTIONS]

Options:
  --dataset NAME      Dataset to search (default: all)
  --top-k INT         Number of results (default: 5)
  --threshold FLOAT   Minimum similarity (default: 0.2)
```

### Create Chat Assistant

```bash
python cli.py create-chat "DSA-110 Assistant" \
    --datasets "DSA-110 Documentation" \
    --prompt "You are an expert on DSA-110..."
```

## MCP Server (Archived)

An old MCP server implementation is preserved as `mcp_server_dormant.py` for
reference only. It is not maintained or recommended; prefer the REST API flows
above.

## Configuration

### Environment Variables

| Variable             | Description                | Default                 |
| -------------------- | -------------------------- | ----------------------- |
| `RAGFLOW_API_KEY`    | API key for authentication | Required                |
| `RAGFLOW_BASE_URL`   | RAGFlow API URL            | `http://localhost:9380` |
| `RAGFLOW_DATASET_ID` | Default dataset ID         | DSA-110 Docs dataset    |
| `RAGFLOW_CHAT_ID`    | Default chat assistant ID  | DSA-110 Assistant       |

### Service URLs

| Service    | URL                         | Description            |
| ---------- | --------------------------- | ---------------------- |
| Web UI     | `http://localhost:9080`     | RAGFlow user interface |
| REST API   | `http://localhost:9380`     | RAGFlow REST API       |
| Custom MCP | Archived (`mcp_server_dormant.py`) | Not recommended        |

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    RAGFlow Stack                            │
├─────────────────────────────────────────────────────────────┤
│  Web UI (9080)  │  API (9380)  │  MCP Server (archived)     │
├─────────────────────────────────────────────────────────────┤
│                    RAGFlow Core                             │
│  - Document Parsing (DeepDoc)                               │
│  - Chunking & Embedding                                     │
│  - Vector Search                                            │
│  - Chat/Agent Orchestration                                 │
├─────────────────────────────────────────────────────────────┤
│  Elasticsearch (1200)  │  MySQL (5455)  │  Redis (16379)    │
│  Vector/Text Index     │  Metadata      │  Cache/Queue      │
├─────────────────────────────────────────────────────────────┤
│                     MinIO (9000-9001)                       │
│                     Document Storage                        │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Connection Refused

Check that RAGFlow is running:

```bash
docker ps | grep ragflow
```

### Authentication Errors

Verify your API key:

```bash
curl -H "Authorization: Bearer $RAGFLOW_API_KEY" \
    http://localhost:9380/api/v1/datasets
```

### No Results

1. Check that documents are uploaded: `list-documents`
2. Check that parsing completed (status should be DONE)
3. Try lowering the similarity threshold: `--threshold 0.1`

## Development

### Module Structure

```
docs/ragflow/
├── __init__.py      # Reference exports (not installed)
├── client.py        # RAGFlow API client wrapper
├── config.py        # Configuration management
├── uploader.py      # Batch document uploader
├── cli.py           # Command-line interface
└── mcp_server_dormant.py  # Archived MCP server (do not use)
```

### Running Tests

```bash
conda activate casa6
cd /data/dsa110-contimg/docs/ragflow
python cli.py --help
```

## See Also

- [RAGFlow Documentation](https://ragflow.io/docs/dev/)
- [RAGFlow GitHub](https://github.com/infiniflow/ragflow)
- [MCP Protocol](https://modelcontextprotocol.io/)
