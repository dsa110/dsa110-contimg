"""
RAGFlow configuration management.

Handles configuration from environment variables and config files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Default configuration values
DEFAULT_BASE_URL = "http://localhost:9380"
DEFAULT_MCP_URL = "http://localhost:9382"
DEFAULT_CHUNK_METHOD = "naive"  # Simple chunking - works without special config
DEFAULT_EMBEDDING_MODEL = ""  # Empty = use server default


@dataclass
class RAGFlowConfig:
    """
    RAGFlow configuration container.
    
    Configuration priority (highest to lowest):
    1. Constructor arguments
    2. Environment variables
    3. Default values
    
    Environment Variables:
        RAGFLOW_API_KEY: API key for authentication
        RAGFLOW_BASE_URL: RAGFlow API base URL (default: http://localhost:9380)
        RAGFLOW_MCP_URL: MCP server URL (default: http://localhost:9382)
        RAGFLOW_EMBEDDING_MODEL: Embedding model (format: model@provider, or empty for default)
        RAGFLOW_CHUNK_METHOD: Document chunking method
    
    Valid chunk_method values:
        naive, book, email, laws, manual, one, paper, picture, presentation, qa, table, tag
    """
    
    api_key: str | None = field(default=None)
    base_url: str = field(default=DEFAULT_BASE_URL)
    mcp_url: str = field(default=DEFAULT_MCP_URL)
    embedding_model: str = field(default=DEFAULT_EMBEDDING_MODEL)
    chunk_method: str = field(default=DEFAULT_CHUNK_METHOD)
    
    # Parser configuration for documents
    parser_config: dict[str, Any] = field(default_factory=lambda: {
        "chunk_token_num": 512,  # Tokens per chunk
        "delimiter": "\\n",
        "html4excel": False,
        "graphrag": {"use_graphrag": False},
        "raptor": {"use_raptor": False},
    })
    
    def __post_init__(self) -> None:
        """Load configuration from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.environ.get("RAGFLOW_API_KEY")
        
        if self.base_url == DEFAULT_BASE_URL:
            self.base_url = os.environ.get("RAGFLOW_BASE_URL", DEFAULT_BASE_URL)
            
        if self.mcp_url == DEFAULT_MCP_URL:
            self.mcp_url = os.environ.get("RAGFLOW_MCP_URL", DEFAULT_MCP_URL)
            
        if self.embedding_model == DEFAULT_EMBEDDING_MODEL:
            self.embedding_model = os.environ.get(
                "RAGFLOW_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
            )
            
        if self.chunk_method == DEFAULT_CHUNK_METHOD:
            self.chunk_method = os.environ.get(
                "RAGFLOW_CHUNK_METHOD", DEFAULT_CHUNK_METHOD
            )
    
    @classmethod
    def from_env(cls) -> RAGFlowConfig:
        """Create configuration from environment variables only."""
        return cls()
    
    @classmethod
    def from_file(cls, config_path: str | Path) -> RAGFlowConfig:
        """
        Load configuration from a YAML or JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            RAGFlowConfig instance
        """
        import json
        
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        content = path.read_text()
        
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise ImportError("PyYAML required for YAML config files")
        else:
            data = json.loads(content)
        
        return cls(**data)
    
    def validate(self) -> list[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        if not self.api_key:
            issues.append("API key not configured (set RAGFLOW_API_KEY)")
        
        if not self.base_url.startswith(("http://", "https://")):
            issues.append(f"Invalid base_url: {self.base_url}")
            
        return issues
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


# DSA-110 specific dataset configurations
# Valid chunk_method: naive, book, email, laws, manual, one, paper, picture, presentation, qa, table, tag
DSA110_DATASETS = {
    "dsa110-docs": {
        "name": "DSA-110 Documentation",
        "description": "Technical documentation for the DSA-110 continuum imaging pipeline",
        "chunk_method": "naive",
        "parser_config": {
            "chunk_token_num": 512,
            "delimiter": "\\n",
        },
    },
    "dsa110-api": {
        "name": "DSA-110 API Reference",
        "description": "API documentation and code references",
        "chunk_method": "naive",
        "parser_config": {
            "chunk_token_num": 256,  # Smaller chunks for code
        },
    },
    "dsa110-guides": {
        "name": "DSA-110 User Guides",
        "description": "Tutorials and how-to guides",
        "chunk_method": "naive",
        "parser_config": {
            "chunk_token_num": 768,  # Larger chunks for narrative
        },
    },
}
