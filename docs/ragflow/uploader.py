"""
Batch document uploader for DSA-110 documentation.

Scans the documentation directory and uploads files to RAGFlow.
"""

from __future__ import annotations

import fnmatch
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from client import RAGFlowClient, RAGFlowError
from config import RAGFlowConfig

logger = logging.getLogger(__name__)

# Default patterns for documentation files
DEFAULT_INCLUDE_PATTERNS = [
    "*.md",
    "*.rst",
    "*.txt",
    "*.html",
]

DEFAULT_EXCLUDE_PATTERNS = [
    "node_modules/*",
    ".git/*",
    "__pycache__/*",
    "*.pyc",
    ".venv/*",
    "venv/*",
    "site/*",  # MkDocs build output
    "build/*",
    "dist/*",
    "_build/*",
    ".tox/*",
    ".mypy_cache/*",
    ".pytest_cache/*",
]


@dataclass
class UploadResult:
    """Result of a document upload operation."""
    
    file_path: Path
    document_id: str | None = None
    success: bool = False
    error: str | None = None
    chunks: int = 0
    
    @property
    def status(self) -> str:
        return "success" if self.success else "failed"


@dataclass
class UploadStats:
    """Statistics for a batch upload operation."""
    
    total_files: int = 0
    uploaded: int = 0
    failed: int = 0
    skipped: int = 0
    total_chunks: int = 0
    duration_seconds: float = 0.0
    results: list[UploadResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.uploaded / self.total_files * 100


class DocumentUploader:
    """
    Batch document uploader for RAGFlow.
    
    Scans directories for documentation files and uploads them
    to a RAGFlow dataset with progress tracking and error handling.
    
    Example:
        >>> uploader = DocumentUploader(client)
        >>> stats = uploader.upload_directory(
        ...     "/data/dsa110-contimg/docs",
        ...     dataset_id="abc123",
        ... )
        >>> print(f"Uploaded {stats.uploaded}/{stats.total_files} files")
    """
    
    def __init__(
        self,
        client: RAGFlowClient | None = None,
        config: RAGFlowConfig | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        batch_size: int = 10,
        parse_after_upload: bool = True,
        wait_for_parsing: bool = True,
        parse_timeout: int = 300,
    ):
        """
        Initialize document uploader.
        
        Args:
            client: RAGFlow client (creates one if not provided)
            config: RAGFlow configuration
            include_patterns: File patterns to include (glob)
            exclude_patterns: File patterns to exclude (glob)
            batch_size: Number of files to upload per request
            parse_after_upload: Start parsing after upload
            wait_for_parsing: Wait for parsing to complete
            parse_timeout: Max seconds to wait for parsing
        """
        self.config = config or RAGFlowConfig()
        self.client = client or RAGFlowClient(config=self.config)
        
        self.include_patterns = include_patterns or DEFAULT_INCLUDE_PATTERNS
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
        self.batch_size = batch_size
        self.parse_after_upload = parse_after_upload
        self.wait_for_parsing = wait_for_parsing
        self.parse_timeout = parse_timeout
    
    def _should_include(self, path: Path, base_dir: Path) -> bool:
        """Check if file should be included based on patterns."""
        relative = str(path.relative_to(base_dir))
        
        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(relative, pattern):
                return False
            # Also check parent directories
            if fnmatch.fnmatch(relative, f"*/{pattern}"):
                return False
        
        # Check include patterns
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return True
        
        return False
    
    def scan_directory(
        self,
        directory: str | Path,
        recursive: bool = True,
    ) -> Generator[Path, None, None]:
        """
        Scan directory for documentation files.
        
        Args:
            directory: Directory to scan
            recursive: Scan subdirectories
            
        Yields:
            Path objects for matching files
        """
        base_dir = Path(directory)
        if not base_dir.exists():
            raise FileNotFoundError(f"Directory not found: {base_dir}")
        
        if not base_dir.is_dir():
            raise ValueError(f"Not a directory: {base_dir}")
        
        pattern = "**/*" if recursive else "*"
        
        for path in base_dir.glob(pattern):
            if path.is_file() and self._should_include(path, base_dir):
                yield path
    
    def upload_file(
        self,
        dataset_id: str,
        file_path: Path,
    ) -> UploadResult:
        """
        Upload a single file.
        
        Args:
            dataset_id: Target dataset ID
            file_path: Path to file
            
        Returns:
            UploadResult with status
        """
        result = UploadResult(file_path=file_path)
        
        try:
            doc = self.client.upload_document(dataset_id, file_path)
            result.document_id = doc.get("id")
            result.success = True
            logger.debug(f"Uploaded: {file_path.name} -> {result.document_id}")
            
        except RAGFlowError as e:
            result.error = str(e)
            logger.warning(f"Upload failed for {file_path.name}: {e}")
            
        except Exception as e:
            result.error = f"Unexpected error: {e}"
            logger.error(f"Unexpected error uploading {file_path.name}: {e}")
        
        return result
    
    def _wait_for_parsing(
        self,
        dataset_id: str,
        document_ids: list[str],
        timeout: int,
    ) -> dict[str, int]:
        """
        Wait for documents to finish parsing.
        
        Args:
            dataset_id: Dataset ID
            document_ids: Document IDs to check
            timeout: Max seconds to wait
            
        Returns:
            Dict mapping document_id to chunk count
        """
        start = time.time()
        pending = set(document_ids)
        results: dict[str, int] = {}
        
        while pending and (time.time() - start) < timeout:
            for doc_id in list(pending):
                try:
                    status = self.client.get_document_status(dataset_id, doc_id)
                    run_status = status.get("run", "").upper()
                    progress = float(status.get("progress", 0))
                    
                    if run_status in ("DONE", "FAIL", "CANCEL") or progress >= 1.0:
                        results[doc_id] = status.get("chunk_count", 0)
                        pending.discard(doc_id)
                        logger.debug(
                            f"Document {doc_id}: {run_status}, "
                            f"{results[doc_id]} chunks"
                        )
                        
                except Exception as e:
                    logger.warning(f"Error checking status for {doc_id}: {e}")
            
            if pending:
                time.sleep(2)  # Poll every 2 seconds
        
        if pending:
            logger.warning(
                f"Parsing timed out for {len(pending)} documents after {timeout}s"
            )
            for doc_id in pending:
                results[doc_id] = 0
        
        return results
    
    def upload_directory(
        self,
        directory: str | Path,
        dataset_id: str,
        recursive: bool = True,
    ) -> UploadStats:
        """
        Upload all documentation files from a directory.
        
        Args:
            directory: Directory to scan
            dataset_id: Target dataset ID
            recursive: Scan subdirectories
            
        Returns:
            UploadStats with results
        """
        stats = UploadStats()
        start_time = time.time()
        
        # Collect files
        files = list(self.scan_directory(directory, recursive))
        stats.total_files = len(files)
        
        logger.info(f"Found {stats.total_files} files to upload from {directory}")
        
        if not files:
            return stats
        
        # Upload in batches
        for i in range(0, len(files), self.batch_size):
            batch = files[i:i + self.batch_size]
            batch_results = []
            
            for file_path in batch:
                result = self.upload_file(dataset_id, file_path)
                stats.results.append(result)
                batch_results.append(result)
                
                if result.success:
                    stats.uploaded += 1
                else:
                    stats.failed += 1
            
            # Parse documents if requested
            if self.parse_after_upload:
                doc_ids = [
                    r.document_id
                    for r in batch_results
                    if r.success and r.document_id
                ]
                
                if doc_ids:
                    try:
                        self.client.parse_documents(dataset_id, doc_ids)
                        
                        if self.wait_for_parsing:
                            chunk_counts = self._wait_for_parsing(
                                dataset_id,
                                doc_ids,
                                self.parse_timeout,
                            )
                            
                            # Update results with chunk counts
                            for result in batch_results:
                                if result.document_id in chunk_counts:
                                    result.chunks = chunk_counts[result.document_id]
                                    stats.total_chunks += result.chunks
                                    
                    except RAGFlowError as e:
                        logger.error(f"Parsing failed: {e}")
            
            logger.info(
                f"Batch {i // self.batch_size + 1}: "
                f"uploaded {len([r for r in batch_results if r.success])}/{len(batch)}"
            )
        
        stats.duration_seconds = time.time() - start_time
        
        logger.info(
            f"Upload complete: {stats.uploaded}/{stats.total_files} files, "
            f"{stats.total_chunks} chunks, {stats.duration_seconds:.1f}s"
        )
        
        return stats


def upload_dsa110_docs(
    api_key: str | None = None,
    docs_dir: str = "/data/dsa110-contimg/docs",
    dataset_name: str = "DSA-110 Documentation",
) -> UploadStats:
    """
    Convenience function to upload DSA-110 documentation.
    
    Args:
        api_key: RAGFlow API key (or set RAGFLOW_API_KEY env var)
        docs_dir: Path to documentation directory
        dataset_name: Name for the dataset
        
    Returns:
        UploadStats with results
    """
    config = RAGFlowConfig(api_key=api_key)
    client = RAGFlowClient(config=config)
    
    # Get or create dataset
    dataset = client.get_or_create_dataset(
        name=dataset_name,
        description="Technical documentation for the DSA-110 continuum imaging pipeline",
        chunk_method="markdown",
    )
    
    uploader = DocumentUploader(client=client)
    return uploader.upload_directory(docs_dir, dataset["id"])
