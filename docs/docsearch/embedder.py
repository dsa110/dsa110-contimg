"""
Embedding generation using OpenAI's text-embedding-3-small model.

Caches embeddings locally to minimize API calls.
"""

import hashlib
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIM = 1536


class Embedder:
    """
    Generate and cache text embeddings using OpenAI API.

    Embeddings are cached in SQLite to avoid redundant API calls.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        cache_db: Optional[Path] = None,
    ):
        """
        Initialize the embedder.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Embedding model name
            cache_db: Path to cache database (default: state/embedding_cache.sqlite3)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.cache_db = cache_db or Path("/data/dsa110-contimg/state/embedding_cache.sqlite3")

        # Lazy-load OpenAI client
        self._client = None

        # Initialize cache
        self._init_cache()

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    def _init_cache(self):
        """Initialize the embedding cache database."""
        self.cache_db.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    text_hash TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_model 
                ON embedding_cache(model)
            """)

    def _hash_text(self, text: str) -> str:
        """Generate a hash for cache lookup."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_cached(self, text: str) -> Optional[list[float]]:
        """Look up cached embedding."""
        text_hash = self._hash_text(text)

        with sqlite3.connect(self.cache_db) as conn:
            row = conn.execute(
                "SELECT embedding FROM embedding_cache WHERE text_hash = ? AND model = ?",
                (text_hash, self.model)
            ).fetchone()

            if row:
                return json.loads(row[0])
        return None

    def _cache_embedding(self, text: str, embedding: list[float]):
        """Store embedding in cache."""
        text_hash = self._hash_text(text)

        with sqlite3.connect(self.cache_db) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embedding_cache (text_hash, model, embedding)
                VALUES (?, ?, ?)
                """,
                (text_hash, self.model, json.dumps(embedding))
            )

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for text, using cache if available.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        # Check cache first
        cached = self._get_cached(text)
        if cached is not None:
            return cached

        # Generate embedding via API
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            embedding = response.data[0].embedding

            # Cache the result
            self._cache_embedding(text, embedding)

            return embedding

        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            raise

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
        show_progress: bool = True,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Uses caching and batches API calls for efficiency.

        Args:
            texts: List of texts to embed
            batch_size: Maximum texts per API call
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        results: list[Optional[list[float]]] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if not uncached_texts:
            return results  # type: ignore

        logger.info(f"Generating {len(uncached_texts)} embeddings ({len(texts) - len(uncached_texts)} cached)")

        # Process uncached texts in batches
        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(range(0, len(uncached_texts), batch_size), desc="Embedding")
            except ImportError:
                iterator = range(0, len(uncached_texts), batch_size)
        else:
            iterator = range(0, len(uncached_texts), batch_size)

        for batch_start in iterator:
            batch_texts = uncached_texts[batch_start:batch_start + batch_size]
            batch_indices = uncached_indices[batch_start:batch_start + batch_size]

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                )

                for j, emb_data in enumerate(response.data):
                    idx = batch_indices[j]
                    embedding = emb_data.embedding
                    results[idx] = embedding

                    # Cache each embedding
                    self._cache_embedding(batch_texts[j], embedding)

            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                raise

        return results  # type: ignore

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        with sqlite3.connect(self.cache_db) as conn:
            total = conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()[0]
            by_model = dict(conn.execute(
                "SELECT model, COUNT(*) FROM embedding_cache GROUP BY model"
            ).fetchall())

        return {
            "total_cached": total,
            "by_model": by_model,
            "cache_db": str(self.cache_db),
        }
