# RAGFlow Integration

RAGFlow provides semantic search and retrieval-augmented generation (RAG) for the DSA-110 project documentation.

## Overview

| Component | URL | Purpose |
|-----------|-----|---------|
| Web UI | http://localhost:9080 | Browser-based chat and dataset management |
| REST API | http://localhost:9380 | Programmatic access to RAG functionality |
| MCP SSE | http://localhost:9382/sse | Model Context Protocol for AI tooling |

## Quick Start

### Check Status

```bash
# Check if RAGFlow container is running
docker ps --filter "name=ragflow"

# Check sync status
python scripts/ragflow_sync.py status
```

### Sync Documentation

```bash
# Preview what would be synced (no changes)
python scripts/ragflow_sync.py sync --dry-run

# Incremental sync (only changed files)
python scripts/ragflow_sync.py sync

# Full re-index (delete all, upload fresh)
python scripts/ragflow_sync.py sync --full
```

### Query via REST API

```bash
# Set API key (get from RAGFlow web UI → System → Settings)
export RAGFLOW_API_KEY="ragflow-xxxxx"

# Query the documentation
curl -s -X POST "http://localhost:9380/api/v1/retrieval" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RAGFLOW_API_KEY" \
  -d '{
    "question": "How do I convert UVH5 files to Measurement Sets?",
    "dataset_ids": ["735f3e9acba011f08a110242ac140006"],
    "top_k": 5
  }' | python -m json.tool
```

## Configuration

Configuration is stored in `config/ragflow.env`:

```bash
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_MCP_SSE_URL=http://localhost:9382/sse
RAGFLOW_MCP_HTTP_URL=http://localhost:9382/mcp
RAGFLOW_DEFAULT_DATASET=DSA-110 Documentation
RAGFLOW_CHUNK_METHOD=markdown
RAGFLOW_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
```

### Getting an API Key

1. Open RAGFlow web UI: http://localhost:9080
2. Navigate to **System → Settings → API**
3. Generate a new API key
4. Save it to your environment:
   ```bash
   export RAGFLOW_API_KEY="ragflow-xxxxx"
   ```

### Dataset ID

The default dataset ID for DSA-110 documentation is:
```
735f3e9acba011f08a110242ac140006
```

You can find dataset IDs via the API:
```bash
curl -s "http://localhost:9380/api/v1/datasets" \
  -H "Authorization: Bearer $RAGFLOW_API_KEY" | python -m json.tool
```

## CLI Commands

The sync tool is at `scripts/ragflow_sync.py`:

### `sync` - Synchronize Documentation

```bash
# Incremental sync - only upload new/modified files
python scripts/ragflow_sync.py sync

# Full re-index - delete everything, upload fresh
python scripts/ragflow_sync.py sync --full

# Dry run - show what would happen without making changes
python scripts/ragflow_sync.py sync --dry-run
```

**What gets synced:**
- `docs/**/*.md` - All markdown documentation
- `backend/src/**/*.py` - Python source code
- `frontend/src/**/*.{ts,tsx}` - Frontend source code

**Excluded:**
- `**/node_modules/**`
- `**/__pycache__/**`
- `**/site/**` (MkDocs build output)
- `**/.git/**`

### `status` - Check Sync Status

```bash
python scripts/ragflow_sync.py status
```

Output:
```
RAGFlow Sync Status
========================================
Local files:     423
Synced (tracked): 423
RAGFlow docs:    423
Total size:      12.34 MB
```

### `progress` - Check Parsing Progress

```bash
python scripts/ragflow_sync.py progress
```

Output:
```
RAGFlow Parsing Progress
==================================================
  DONE       ████████████████████ 400 (94.6%)
  RUNNING    ░░░░░░░░░░░░░░░░░░░░  20 (4.7%)
  PENDING    ░░░░░░░░░░░░░░░░░░░░   3 (0.7%)

Total: 423 documents
Chunks: 12,456
Tokens: 1,234,567
```

### `clear` - Clear Local Sync State

```bash
# Clear local tracking database (doesn't affect RAGFlow)
python scripts/ragflow_sync.py clear
```

## REST API Reference

### Authentication

All API requests require a Bearer token:
```
Authorization: Bearer ragflow-xxxxx
```

### Retrieval (Query)

```http
POST /api/v1/retrieval
Content-Type: application/json

{
  "question": "your question here",
  "dataset_ids": ["735f3e9acba011f08a110242ac140006"],
  "top_k": 5,
  "similarity_threshold": 0.2
}
```

Response:
```json
{
  "code": 0,
  "data": {
    "chunks": [
      {
        "content": "matched text...",
        "similarity": 0.85,
        "document_name": "docs/guides/conversion.md"
      }
    ]
  }
}
```

### List Datasets

```http
GET /api/v1/datasets
```

### List Documents in Dataset

```http
GET /api/v1/datasets/{dataset_id}/documents?page=1&page_size=100
```

### Upload Document

```http
POST /api/v1/datasets/{dataset_id}/documents
Content-Type: multipart/form-data

file: (binary)
```

### Delete Documents

```http
DELETE /api/v1/datasets/{dataset_id}/documents
Content-Type: application/json

{
  "ids": ["doc_id_1", "doc_id_2"]
}
```

### Trigger Parsing

After uploading documents, trigger parsing to create embeddings:

```http
POST /api/v1/datasets/{dataset_id}/chunks
Content-Type: application/json

{
  "document_ids": ["doc_id_1", "doc_id_2"]
}
```

## MCP Integration

RAGFlow exposes an MCP (Model Context Protocol) server for AI tool integration.

### VS Code Configuration

Add to `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "ragflow": {
      "type": "sse",
      "url": "http://localhost:9382/sse",
      "headers": {
        "Authorization": "Bearer ${env:RAGFLOW_API_KEY}"
      }
    }
  }
}
```

### Testing MCP Connection

```bash
# Test MCP SSE endpoint
python scripts/test_ragflow_mcp_dormant.py

# Query via MCP
python scripts/test_ragflow_mcp_dormant.py --query "How do I run calibration?"
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `retrieve_documents` | Query documents by semantic similarity |
| `list_datasets` | List available datasets |
| `get_document` | Get document content by ID |

## Troubleshooting

### Container Not Running

```bash
# Start RAGFlow (requires docker compose in ops/docker/)
cd /data/dsa110-contimg/ops/docker
docker compose -f docker-compose.ragflow.yml up -d
```

### API Returns 401 Unauthorized

- Check your API key is correct
- API keys expire - generate a new one from the web UI
- Ensure you're using `Bearer` prefix: `Authorization: Bearer ragflow-xxxxx`

### Documents Not Appearing

1. Check if upload succeeded:
   ```bash
   python scripts/ragflow_sync.py status
   ```

2. Check parsing progress:
   ```bash
   python scripts/ragflow_sync.py progress
   ```

3. Re-sync if needed:
   ```bash
   python scripts/ragflow_sync.py sync --full
   ```

### Embedding Model Not Found

If RAGFlow can't find the embedding model, ensure the model is configured:
```bash
python scripts/configure_ragflow_openai.py
```

### Slow Parsing

RAGFlow uses CPU-based embedding by default. For large document sets:
- Expect ~5-10 minutes for full re-index of 400+ documents
- Check progress with `python scripts/ragflow_sync.py progress`
- Consider using GPU-enabled RAGFlow for faster processing

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Local Files   │     │  Sync Script    │     │    RAGFlow      │
│                 │────▶│                 │────▶│    Docker       │
│  docs/*.md      │     │ ragflow_sync.py │     │                 │
│  backend/*.py   │     │                 │     │  ┌───────────┐  │
│  frontend/*.ts  │     │  ┌───────────┐  │     │  │ Embedding │  │
│                 │     │  │ SQLite    │  │     │  │   Model   │  │
│                 │     │  │ tracking  │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
└─────────────────┘     └─────────────────┘     │  ┌───────────┐  │
                                                │  │ Vector DB │  │
                                                │  └───────────┘  │
                                                └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │   REST API      │
                                                │   :9380         │
                                                ├─────────────────┤
                                                │   MCP SSE       │
                                                │   :9382         │
                                                ├─────────────────┤
                                                │   Web UI        │
                                                │   :9080         │
                                                └─────────────────┘
```

## Related Documentation

- **DocSearch** - Local SQLite-based semantic search (see [DocSearch Guide](../docsearch/README.md))
- **Configuration** - See `config/ragflow.env` for all settings
- **Scripts** - See `scripts/README.md` for other utility scripts
