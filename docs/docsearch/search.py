"""
SQLite-based vector search for documentation.

Uses sqlite-vec for efficient similarity search without external services.
"""

import hashlib
import json
import logging
import os
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sqlite_vec

from .chunker import Chunk, chunk_document, iter_documents
from .embedder import Embedder, EMBEDDING_DIM

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with metadata."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    heading: str
    score: float

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "file": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "heading": self.heading,
            "score": self.score,
        }


def serialize_embedding(embedding: list[float]) -> bytes:
    """Serialize embedding to bytes for sqlite-vec."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def deserialize_embedding(data: bytes) -> list[float]:
    """Deserialize embedding from bytes."""
    count = len(data) // 4
    return list(struct.unpack(f"{count}f", data))


class DocSearch:
    """
    Local documentation search using SQLite and vector embeddings.

    This provides a fully local, service-free search capability using
    sqlite-vec for vector similarity search.

    Example:
        >>> search = DocSearch()
        >>> search.index_directory("/data/dsa110-contimg/docs")
        >>> results = search.search("How do I run calibration?")
        >>> for r in results:
        ...     print(f"{r.score:.3f}: {r.heading} ({r.file_path})")
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        embedder: Optional[Embedder] = None,
    ):
        """
        Initialize the search index.

        Args:
            db_path: Path to SQLite database (default: state/docsearch.sqlite3)
            embedder: Embedder instance (default: creates new one)
        """
        self.db_path = Path(db_path or "/data/dsa110-contimg/state/docsearch.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize embedder (may raise if no API key)
        self._embedder = embedder

        # Initialize database
        self._init_db()

    @property
    def embedder(self) -> Embedder:
        """Lazy-load embedder."""
        if self._embedder is None:
            self._embedder = Embedder()
        return self._embedder

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection with sqlite-vec loaded."""
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_conn() as conn:
            # Main chunks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    heading TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for efficient lookup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_file 
                ON chunks(file_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_hash 
                ON chunks(file_hash)
            """)

            # Vector table for embeddings (using sqlite-vec)
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings 
                USING vec0(
                    chunk_id INTEGER PRIMARY KEY,
                    embedding FLOAT[{EMBEDDING_DIM}]
                )
            """)

            # File tracking table for incremental updates
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indexed_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _file_hash(self, path: Path) -> str:
        """Compute hash of file for change detection."""
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _needs_reindex(self, path: Path, file_hash: str) -> bool:
        """Check if file needs to be re-indexed."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT file_hash FROM indexed_files WHERE file_path = ?",
                (str(path),)
            ).fetchone()

            if row is None:
                return True
            return row[0] != file_hash

    def _remove_file_chunks(self, path: Path):
        """Remove existing chunks for a file."""
        with self._get_conn() as conn:
            # Get chunk IDs to remove from vector table
            chunk_ids = [
                row[0] for row in conn.execute(
                    "SELECT id FROM chunks WHERE file_path = ?",
                    (str(path),)
                ).fetchall()
            ]

            # Remove from vector table
            for chunk_id in chunk_ids:
                conn.execute(
                    "DELETE FROM chunk_embeddings WHERE chunk_id = ?",
                    (chunk_id,)
                )

            # Remove from chunks table
            conn.execute(
                "DELETE FROM chunks WHERE file_path = ?",
                (str(path),)
            )

            # Remove from indexed files
            conn.execute(
                "DELETE FROM indexed_files WHERE file_path = ?",
                (str(path),)
            )

    def index_file(
        self,
        path: Path,
        content: Optional[str] = None,
        force: bool = False,
    ) -> int:
        """
        Index a single file.

        Args:
            path: File path
            content: File content (read from path if not provided)
            force: Re-index even if unchanged

        Returns:
            Number of chunks indexed
        """
        path = Path(path)

        if content is None:
            content = path.read_text(encoding="utf-8", errors="replace")

        file_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if reindex needed
        if not force and not self._needs_reindex(path, file_hash):
            logger.debug(f"Skipping unchanged file: {path}")
            return 0

        # Remove existing chunks
        self._remove_file_chunks(path)

        # Chunk the document
        chunks = chunk_document(content, str(path))

        if not chunks:
            return 0

        # Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = self.embedder.embed_batch(texts, show_progress=False)

        # Insert chunks and embeddings
        with self._get_conn() as conn:
            for chunk, embedding in zip(chunks, embeddings):
                # Insert chunk
                cursor = conn.execute(
                    """
                    INSERT INTO chunks (content, file_path, file_hash, start_line, end_line, heading)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (chunk.content, chunk.file_path, file_hash,
                     chunk.start_line, chunk.end_line, chunk.heading)
                )
                chunk_id = cursor.lastrowid

                # Insert embedding
                conn.execute(
                    "INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, serialize_embedding(embedding))
                )

            # Update indexed files tracking
            conn.execute(
                """
                INSERT OR REPLACE INTO indexed_files (file_path, file_hash)
                VALUES (?, ?)
                """,
                (str(path), file_hash)
            )

        return len(chunks)

    def index_directory(
        self,
        directory: Path,
        extensions: tuple[str, ...] = (".md", ".txt", ".rst"),
        exclude_patterns: tuple[str, ...] = ("__pycache__", ".git", "node_modules", "site"),
        force: bool = False,
        show_progress: bool = True,
    ) -> dict:
        """
        Index all documents in a directory.

        Args:
            directory: Root directory to scan
            extensions: File extensions to include
            exclude_patterns: Directory names to exclude
            force: Re-index all files even if unchanged
            show_progress: Show progress bar

        Returns:
            Statistics about the indexing operation
        """
        directory = Path(directory)

        # Collect files to process
        files = list(iter_documents(directory, extensions, exclude_patterns))

        logger.info(f"Found {len(files)} files to process")

        stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_indexed": 0,
            "errors": [],
        }

        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(files, desc="Indexing")
            except ImportError:
                iterator = files
        else:
            iterator = files

        for path, content in iterator:
            try:
                chunks_added = self.index_file(path, content, force=force)
                if chunks_added > 0:
                    stats["files_processed"] += 1
                    stats["chunks_indexed"] += chunks_added
                else:
                    stats["files_skipped"] += 1
            except Exception as e:
                logger.warning(f"Error indexing {path}: {e}")
                stats["errors"].append({"file": str(path), "error": str(e)})

        logger.info(
            f"Indexed {stats['files_processed']} files ({stats['chunks_indexed']} chunks), "
            f"skipped {stats['files_skipped']} unchanged"
        )

        return stats

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """
        Search the index for relevant documents.

        Args:
            query: Search query
            top_k: Maximum number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query)
        query_bytes = serialize_embedding(query_embedding)

        # Search using sqlite-vec
        with self._get_conn() as conn:
            # vec_distance_cosine returns distance (0 = identical), convert to similarity
            results = conn.execute(
                """
                SELECT 
                    c.content,
                    c.file_path,
                    c.start_line,
                    c.end_line,
                    c.heading,
                    1 - vec_distance_cosine(e.embedding, ?) as similarity
                FROM chunk_embeddings e
                JOIN chunks c ON c.id = e.chunk_id
                WHERE similarity >= ?
                ORDER BY similarity DESC
                LIMIT ?
                """,
                (query_bytes, min_score, top_k)
            ).fetchall()

        return [
            SearchResult(
                content=row[0],
                file_path=row[1],
                start_line=row[2],
                end_line=row[3],
                heading=row[4] or "",
                score=row[5],
            )
            for row in results
        ]

    def get_stats(self) -> dict:
        """Get index statistics."""
        with self._get_conn() as conn:
            total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            total_files = conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]
            indexed_files = conn.execute("SELECT COUNT(*) FROM indexed_files").fetchone()[0]

        embedder_stats = {}
        if self._embedder:
            embedder_stats = self._embedder.get_cache_stats()

        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "indexed_files": indexed_files,
            "db_path": str(self.db_path),
            "embedding_cache": embedder_stats,
        }

    def clear(self):
        """Clear all indexed data."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM chunk_embeddings")
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM indexed_files")

        logger.info("Cleared all indexed data")
