# RAGFlow Integration

This module provides integration with [RAGFlow](https://ragflow.io/) for
documentation retrieval using RAG (Retrieval-Augmented Generation).

## Overview

RAGFlow is deployed locally to provide:

- **Document indexing** for DSA-110 documentation
- **Semantic search** with embedding-based retrieval
- **MCP server** for AI agent integration

## Quick Start

### 1. Set Up API Key

First, create an account and get an API key:

1. Open http://localhost:9080 in your browser
2. Register or log in
3. Go to **Settings** → **API Keys**
4. Create a new API key
5. Export the key:

```bash
export RAGFLOW_API_KEY="ragflow-xxxxxxxxxxxxxxxxxxxxx"
```

### 2. Upload Documentation

Upload the DSA-110 documentation:

```bash
conda activate casa6

# Upload all docs with default settings
python -m dsa110_contimg.ragflow.cli upload \
    --api-key $RAGFLOW_API_KEY

# Or upload a specific directory
python -m dsa110_contimg.ragflow.cli upload \
    --docs-dir /data/dsa110-contimg/docs \
    --dataset "DSA-110 Documentation" \
    --api-key $RAGFLOW_API_KEY
```

### 3. Query the Knowledge Base

```bash
# Search for information
python -m dsa110_contimg.ragflow.cli query \
    "How do I convert UVH5 files to Measurement Sets?" \
    --api-key $RAGFLOW_API_KEY
```

### 4. Use from Python

```python
from dsa110_contimg.ragflow import RAGFlowClient

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

## CLI Commands

### Upload Documents

```bash
python -m dsa110_contimg.ragflow.cli upload [OPTIONS]

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
python -m dsa110_contimg.ragflow.cli list-datasets
```

### List Documents

```bash
python -m dsa110_contimg.ragflow.cli list-documents "DSA-110 Documentation"
```

### Query

```bash
python -m dsa110_contimg.ragflow.cli query "your question" [OPTIONS]

Options:
  --dataset NAME      Dataset to search (default: all)
  --top-k INT         Number of results (default: 5)
  --threshold FLOAT   Minimum similarity (default: 0.2)
```

### Create Chat Assistant

```bash
python -m dsa110_contimg.ragflow.cli create-chat "DSA-110 Assistant" \
    --datasets "DSA-110 Documentation" \
    --prompt "You are an expert on DSA-110..."
```

## MCP Server Integration

This module includes a custom MCP (Model Context Protocol) server that exposes
RAGFlow's retrieval capabilities as tools for VS Code/Copilot and other AI
agents.

### Start the MCP Server

```bash
# Activate environment
conda activate casa6

# Start MCP server on port 9400
export RAGFLOW_API_KEY="your-api-key"
python -m dsa110_contimg.ragflow.mcp_server --sse --port 9400

# Or use systemd
sudo cp ops/systemd/ragflow-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start ragflow-mcp
```

### VS Code GitHub Copilot

The MCP configuration is in `.vscode/mcp.json`:

```json
{
  "servers": {
    "ragflow-dsa110": {
      "type": "sse",
      "url": "http://localhost:9400/sse",
      "description": "DSA-110 documentation search via RAGFlow"
    }
  }
}
```

### Available MCP Tools

The MCP server exposes these tools:

1. **search_dsa110_docs**: Search documentation with a query

   - Parameters: `query` (string), `top_k` (integer, optional)
   - Returns: Relevant document chunks with similarity scores

2. **ask_dsa110_assistant**: Ask a question to the chat assistant
   - Parameters: `question` (string)
   - Returns: AI-generated answer with source citations

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ragflow-dsa110": {
      "command": "python",
      "args": ["-m", "dsa110_contimg.ragflow.mcp_server", "--stdio"],
      "env": {
        "RAGFLOW_API_KEY": "YOUR_API_KEY",
        "RAGFLOW_BASE_URL": "http://localhost:9380"
      }
    }
  }
}
```

### Test MCP Connection

```bash
# Health check
curl http://localhost:9400/health

# SSE endpoint test (should return session endpoint)
curl -H "Accept: text/event-stream" http://localhost:9400/sse
```

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
| Custom MCP | `http://localhost:9400/sse` | Our MCP server (SSE)   |

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    RAGFlow Stack                            │
├─────────────────────────────────────────────────────────────┤
│  Web UI (9080)  │  API (9380)  │  MCP Server (9382)         │
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

### MCP Connection Issues

1. Ensure API key is set in environment
2. Check MCP endpoint responds:
   ```bash
   curl -v http://localhost:9382/sse -H "api_key: $RAGFLOW_API_KEY"
   ```

## Development

### Module Structure

```
backend/src/dsa110_contimg/ragflow/
├── __init__.py      # Package exports
├── client.py        # RAGFlow API client
├── config.py        # Configuration management
├── uploader.py      # Batch document uploader
└── cli.py           # Command-line interface
```

### Running Tests

```bash
conda activate casa6
python -m pytest backend/tests/ragflow/ -v
```

## See Also

- [RAGFlow Documentation](https://ragflow.io/docs/dev/)
- [RAGFlow GitHub](https://github.com/infiniflow/ragflow)
- [MCP Protocol](https://modelcontextprotocol.io/)
