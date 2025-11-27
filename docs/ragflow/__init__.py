"""
RAGFlow Integration - Reference Implementation

**LOCATION:** This module has been moved to `docs/ragflow/` and is provided as
**reference code and examples only**. It is no longer part of the
`dsa110_contimg` Python package.

**Recommended Usage:**

For lightweight documentation search, use `dsa110_contimg.docsearch` instead:

    >>> from dsa110_contimg.docsearch import DocSearch
    >>> search = DocSearch()
    >>> results = search.search("your query")

For RAGFlow integration:

1. Deploy RAGFlow containers (see `docs/ops/ragflow/README.md`)
2. Access via REST API at `localhost:9380` or web UI at `localhost:9080`
3. Use the standalone scripts in this directory:

    ```bash
    # Run scripts directly from docs/ragflow/
    cd /data/dsa110-contimg/docs/ragflow
    python cli.py query "your question"
    python cli.py upload --docs-dir /path/to/docs
    ```

MCP Server:
    Run the MCP server for AI agent integration:
    
    ```bash
    cd /data/dsa110-contimg/docs/ragflow
    python mcp_server.py --sse --port 9400
    ```

**Note:** These files are examples and require manual setup. They are not
automatically installed or imported by the pipeline.
"""

# These imports only work when running scripts directly from this directory
# They are NOT available via `from dsa110_contimg.ragflow import ...`
try:
    from client import RAGFlowClient
    from uploader import DocumentUploader
    from config import RAGFlowConfig
    
    __all__ = [
        "RAGFlowClient",
        "DocumentUploader",
        "RAGFlowConfig",
    ]
except ImportError:
    # This is expected - module is documentation/examples only
    __all__ = []
