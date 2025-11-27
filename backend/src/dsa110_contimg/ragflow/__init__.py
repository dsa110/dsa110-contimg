"""
RAGFlow integration for DSA-110 documentation retrieval.

This module provides SDK wrappers and utilities for:
- Document upload and management
- Knowledge base creation and configuration
- Chat/retrieval sessions
- MCP server integration for agent access

Configuration:
    Set RAGFLOW_API_KEY and RAGFLOW_BASE_URL environment variables,
    or use the RAGFlowClient constructor directly.

Example:
    >>> from dsa110_contimg.ragflow import RAGFlowClient
    >>> client = RAGFlowClient()
    >>> datasets = client.list_datasets()

MCP Server:
    The module includes an MCP server for VS Code/Copilot integration:
    
    >>> python -m dsa110_contimg.ragflow.mcp_server --sse --port 9400
    
    Or configure in .vscode/mcp.json:
    {
        "servers": {
            "ragflow-dsa110": {
                "type": "sse",
                "url": "http://localhost:9400/sse"
            }
        }
    }
"""

from .client import RAGFlowClient
from .uploader import DocumentUploader
from .config import RAGFlowConfig

__all__ = [
    "RAGFlowClient",
    "DocumentUploader",
    "RAGFlowConfig",
]
