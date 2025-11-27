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
"""

from .client import RAGFlowClient
from .uploader import DocumentUploader
from .config import RAGFlowConfig

__all__ = [
    "RAGFlowClient",
    "DocumentUploader",
    "RAGFlowConfig",
]
