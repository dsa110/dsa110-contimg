"""
RAGFlow SDK client wrapper for DSA-110.

Provides a simplified interface to the RAGFlow API with
DSA-110 specific defaults and error handling.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from .config import RAGFlowConfig, DSA110_DATASETS

logger = logging.getLogger(__name__)


class RAGFlowError(Exception):
    """Base exception for RAGFlow operations."""
    
    def __init__(self, message: str, code: int | None = None, details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


class RAGFlowClient:
    """
    RAGFlow API client for document and dataset management.
    
    This client wraps the RAGFlow REST API and provides:
    - Dataset creation and management
    - Document upload and parsing
    - Retrieval queries
    - Chat session management
    
    Example:
        >>> client = RAGFlowClient(api_key="your-key")
        >>> dataset = client.create_dataset("my-docs")
        >>> client.upload_document(dataset["id"], "README.md")
        >>> results = client.retrieve(["dataset-id"], "How do I convert UVH5?")
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        config: RAGFlowConfig | None = None,
        timeout: int = 60,
    ):
        """
        Initialize RAGFlow client.
        
        Args:
            api_key: RAGFlow API key (overrides config/env)
            base_url: RAGFlow API URL (overrides config/env)
            config: RAGFlowConfig instance (uses defaults if None)
            timeout: Request timeout in seconds
        """
        self.config = config or RAGFlowConfig()
        
        # Allow overrides
        if api_key:
            self.config.api_key = api_key
        if base_url:
            self.config.base_url = base_url
            
        self.timeout = timeout
        self.api_url = f"{self.config.base_url}/api/v1"
        
        # Validate configuration
        issues = self.config.validate()
        if issues:
            logger.warning(f"Configuration issues: {issues}")
    
    @property
    def _headers(self) -> dict[str, str]:
        """Get authorization headers."""
        if not self.config.api_key:
            return {}
        return {"Authorization": f"Bearer {self.config.api_key}"}
    
    def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        params: dict | None = None,
        files: list | None = None,
    ) -> dict[str, Any]:
        """
        Make an API request.
        
        Args:
            method: HTTP method
            path: API path (appended to api_url)
            json_data: JSON body data
            params: Query parameters
            files: Files for multipart upload
            
        Returns:
            Response data dict
            
        Raises:
            RAGFlowError: If request fails
        """
        url = f"{self.api_url}{path}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                files=files,
                headers=self._headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise RAGFlowError(
                    message=data.get("message", "Unknown error"),
                    code=data.get("code"),
                    details=data,
                )
            
            return data.get("data", {})
            
        except requests.exceptions.RequestException as e:
            raise RAGFlowError(f"Request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise RAGFlowError(f"Invalid JSON response: {e}") from e
    
    # -------------------------------------------------------------------------
    # Health & Status
    # -------------------------------------------------------------------------
    
    def health_check(self) -> bool:
        """
        Check if RAGFlow API is accessible.
        
        Returns:
            True if API responds, False otherwise
        """
        try:
            # Try to list datasets (requires auth)
            self.list_datasets(page_size=1)
            return True
        except RAGFlowError:
            return False
        except Exception:
            return False
    
    # -------------------------------------------------------------------------
    # Dataset Management
    # -------------------------------------------------------------------------
    
    def create_dataset(
        self,
        name: str,
        description: str | None = None,
        embedding_model: str | None = None,
        chunk_method: str | None = None,
        parser_config: dict | None = None,
        permission: str = "me",
    ) -> dict[str, Any]:
        """
        Create a new dataset (knowledge base).
        
        Args:
            name: Dataset name
            description: Dataset description
            embedding_model: Embedding model (uses config default)
            chunk_method: Chunking method (uses config default)
            parser_config: Parser configuration dict
            permission: Access permission ("me" or "team")
            
        Returns:
            Created dataset info dict
        """
        payload = {
            "name": name,
            "description": description,
            "chunk_method": chunk_method or self.config.chunk_method,
            "permission": permission,
        }
        
        # Only include embedding_model if explicitly set (non-empty)
        emb_model = embedding_model or self.config.embedding_model
        if emb_model:
            payload["embedding_model"] = emb_model
        
        if parser_config:
            payload["parser_config"] = parser_config
        elif self.config.parser_config:
            payload["parser_config"] = self.config.parser_config
            
        logger.info(f"Creating dataset: {name}")
        return self._request("POST", "/datasets", json_data=payload)
    
    def create_dsa110_dataset(self, dataset_key: str = "dsa110-docs") -> dict[str, Any]:
        """
        Create a dataset with DSA-110 specific configuration.
        
        Args:
            dataset_key: Key from DSA110_DATASETS config
            
        Returns:
            Created dataset info dict
        """
        if dataset_key not in DSA110_DATASETS:
            raise ValueError(f"Unknown dataset key: {dataset_key}")
        
        config = DSA110_DATASETS[dataset_key]
        return self.create_dataset(
            name=config["name"],
            description=config["description"],
            chunk_method=config.get("chunk_method"),
            parser_config=config.get("parser_config"),
        )
    
    def list_datasets(
        self,
        page: int = 1,
        page_size: int = 30,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List available datasets.
        
        Args:
            page: Page number
            page_size: Results per page
            name: Filter by name
            
        Returns:
            List of dataset info dicts
        """
        params = {
            "page": page,
            "page_size": page_size,
            "orderby": "create_time",
            "desc": True,
        }
        if name:
            params["name"] = name
            
        return self._request("GET", "/datasets", params=params)
    
    def get_dataset(self, name: str) -> dict[str, Any] | None:
        """
        Get a dataset by name.
        
        Args:
            name: Dataset name
            
        Returns:
            Dataset info dict or None if not found
        """
        datasets = self.list_datasets(name=name)
        return datasets[0] if datasets else None
    
    def get_or_create_dataset(
        self,
        name: str,
        **create_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Get existing dataset or create new one.
        
        If a dataset with the same name exists but belongs to another user,
        appends a suffix to create a unique dataset name.
        
        Args:
            name: Dataset name
            **create_kwargs: Arguments for create_dataset
            
        Returns:
            Dataset info dict
        """
        existing = self.get_dataset(name)
        if existing:
            logger.info(f"Using existing dataset: {name}")
            return existing
        
        # Try to create with the original name
        try:
            return self.create_dataset(name, **create_kwargs)
        except RAGFlowError as e:
            # If permission error (name exists but owned by another user),
            # try with a unique suffix
            if "permission" in str(e).lower() or "exists" in str(e).lower():
                import time
                unique_name = f"{name} ({int(time.time()) % 10000})"
                logger.warning(
                    f"Dataset '{name}' exists but not accessible. "
                    f"Creating '{unique_name}' instead."
                )
                return self.create_dataset(unique_name, **create_kwargs)
            raise
    
    def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset by ID."""
        self._request("DELETE", "/datasets", json_data={"ids": [dataset_id]})
        logger.info(f"Deleted dataset: {dataset_id}")
    
    # -------------------------------------------------------------------------
    # Document Management
    # -------------------------------------------------------------------------
    
    def upload_document(
        self,
        dataset_id: str,
        file_path: str | Path,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a document to a dataset.
        
        Args:
            dataset_id: Target dataset ID
            file_path: Path to document file
            display_name: Display name (defaults to filename)
            
        Returns:
            Document info dict
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        
        name = display_name or path.name
        content = path.read_bytes()
        
        files = [("file", (name, content))]
        
        logger.info(f"Uploading document: {name} to dataset {dataset_id}")
        result = self._request(
            "POST",
            f"/datasets/{dataset_id}/documents",
            files=files,
        )
        
        # Return first document (we only uploaded one)
        if isinstance(result, list) and result:
            return result[0]
        return result
    
    def upload_documents(
        self,
        dataset_id: str,
        file_paths: list[str | Path],
    ) -> list[dict[str, Any]]:
        """
        Upload multiple documents to a dataset.
        
        Args:
            dataset_id: Target dataset ID
            file_paths: List of document paths
            
        Returns:
            List of document info dicts
        """
        files = []
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Skipping missing file: {path}")
                continue
            files.append(("file", (path.name, path.read_bytes())))
        
        if not files:
            return []
        
        logger.info(f"Uploading {len(files)} documents to dataset {dataset_id}")
        return self._request(
            "POST",
            f"/datasets/{dataset_id}/documents",
            files=files,
        )
    
    def list_documents(
        self,
        dataset_id: str,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List documents in a dataset.
        
        Args:
            dataset_id: Dataset ID
            page: Page number
            page_size: Results per page
            
        Returns:
            List of document info dicts
        """
        params = {
            "page": page,
            "page_size": page_size,
            "orderby": "create_time",
            "desc": True,
        }
        result = self._request(
            "GET",
            f"/datasets/{dataset_id}/documents",
            params=params,
        )
        return result.get("docs", [])
    
    def parse_documents(
        self,
        dataset_id: str,
        document_ids: list[str],
    ) -> None:
        """
        Start parsing documents (async).
        
        Args:
            dataset_id: Dataset ID
            document_ids: List of document IDs to parse
        """
        logger.info(f"Starting parse for {len(document_ids)} documents")
        self._request(
            "POST",
            f"/datasets/{dataset_id}/chunks",
            json_data={"document_ids": document_ids},
        )
    
    def get_document_status(
        self,
        dataset_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        """
        Get document parsing status.
        
        Args:
            dataset_id: Dataset ID
            document_id: Document ID
            
        Returns:
            Document info with status
        """
        docs = self._request(
            "GET",
            f"/datasets/{dataset_id}/documents",
            params={"id": document_id},
        )
        docs_list = docs.get("docs", [])
        return docs_list[0] if docs_list else {}
    
    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------
    
    def retrieve(
        self,
        dataset_ids: list[str],
        question: str,
        document_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 10,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_k: int = 1024,
        keyword: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a question.
        
        Args:
            dataset_ids: Dataset IDs to search
            question: Query question
            document_ids: Optional document filter
            page: Result page
            page_size: Results per page
            similarity_threshold: Minimum similarity score
            vector_similarity_weight: Weight for vector vs keyword
            top_k: Max candidates for reranking
            keyword: Enable keyword search
            
        Returns:
            List of chunk results with scores
        """
        payload = {
            "dataset_ids": dataset_ids,
            "document_ids": document_ids or [],
            "question": question,
            "page": page,
            "page_size": page_size,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "top_k": top_k,
            "keyword": keyword,
        }
        
        result = self._request("POST", "/retrieval", json_data=payload)
        return result.get("chunks", [])
    
    # -------------------------------------------------------------------------
    # Chat
    # -------------------------------------------------------------------------
    
    def create_chat(
        self,
        name: str,
        dataset_ids: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a chat assistant linked to datasets.
        
        Args:
            name: Chat assistant name
            dataset_ids: Datasets to use for retrieval
            system_prompt: Custom system prompt
            
        Returns:
            Chat assistant info dict
        """
        prompt_config = {
            "similarity_threshold": 0.2,
            "keywords_similarity_weight": 0.7,
            "top_n": 8,
            "top_k": 1024,
            "variables": [{"key": "knowledge", "optional": True}],
            "show_quote": True,
        }
        
        if system_prompt:
            prompt_config["prompt"] = system_prompt
        else:
            prompt_config["prompt"] = (
                "You are an expert on the DSA-110 radio telescope and continuum imaging pipeline. "
                "Use the knowledge base to answer questions accurately and technically. "
                "If information is not in the knowledge base, say so clearly. "
                "Here is the knowledge base:\n{knowledge}\n"
            )
        
        payload = {
            "name": name,
            "dataset_ids": dataset_ids,
            "prompt": prompt_config,
        }
        
        return self._request("POST", "/chats", json_data=payload)
    
    def list_chats(
        self,
        page: int = 1,
        page_size: int = 30,
    ) -> list[dict[str, Any]]:
        """List available chat assistants."""
        return self._request(
            "GET",
            "/chats",
            params={"page": page, "page_size": page_size},
        )
