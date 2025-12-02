#!/usr/bin/env python3
"""
RAGFlow Incremental Sync for DSA-110 Documentation.

This script provides "reloadable" indexing by:
1. Tracking file hashes in a local SQLite database
2. Only uploading new or modified files
3. Deleting documents for files that no longer exist
4. Supporting dry-run mode to preview changes

Usage:
    # Sync all docs (incremental)
    python ragflow_sync.py sync
    
    # Full re-index (delete all, upload fresh)
    python ragflow_sync.py sync --full
    
    # Dry run (preview changes)
    python ragflow_sync.py sync --dry-run
    
    # Show current state
    python ragflow_sync.py status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.environ.get("RAGFLOW_API_KEY", "ragflow-Y1ZjQwNWFjY2I5ZjExZjA5MGU5MDI0Mm")
BASE_URL = os.environ.get("RAGFLOW_BASE_URL", "http://localhost:9380")
DATASET_ID = os.environ.get("RAGFLOW_DATASET_ID", "735f3e9acba011f08a110242ac140006")
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/data/dsa110-contimg"))
STATE_DB = Path(os.environ.get("RAGFLOW_STATE_DB", "/data/dsa110-contimg/state/db/ragflow_sync.sqlite3"))

# Source directories and their file patterns
# Each entry: (relative_path, [patterns])
SOURCE_DIRS = [
    ("docs", ["*.md", "*.txt", "*.rst"]),
    ("backend/src", ["*.py"]),
    ("frontend/src", ["*.ts", "*.tsx", "*.js", "*.jsx"]),
]

# Global exclude patterns (applied to all sources)
EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**", 
    "**/venv/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
    "**/coverage/**",
]


@dataclass
class FileInfo:
    """Information about a file for tracking changes."""
    path: str
    hash: str
    mtime: float
    size: int
    
    @classmethod
    def from_path(cls, path: Path, base_dir: Path) -> "FileInfo":
        """Create FileInfo from a file path."""
        stat = path.stat()
        with open(path, "rb") as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
        return cls(
            path=str(path.relative_to(base_dir)),
            hash=content_hash,
            mtime=stat.st_mtime,
            size=stat.st_size,
        )


class SyncDatabase:
    """SQLite database for tracking sync state."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS synced_files (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                mtime REAL NOT NULL,
                size INTEGER NOT NULL,
                ragflow_doc_id TEXT,
                synced_at TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_hash ON synced_files(hash);
            CREATE INDEX IF NOT EXISTS idx_ragflow_doc ON synced_files(ragflow_doc_id);
        """)
        self.conn.commit()
    
    def get_synced_file(self, path: str) -> dict | None:
        """Get sync info for a file."""
        cur = self.conn.execute(
            "SELECT path, hash, mtime, size, ragflow_doc_id, synced_at FROM synced_files WHERE path = ?",
            (path,)
        )
        row = cur.fetchone()
        if row:
            return {
                "path": row[0],
                "hash": row[1],
                "mtime": row[2],
                "size": row[3],
                "ragflow_doc_id": row[4],
                "synced_at": row[5],
            }
        return None
    
    def get_all_synced(self) -> list[dict]:
        """Get all synced files."""
        cur = self.conn.execute(
            "SELECT path, hash, mtime, size, ragflow_doc_id, synced_at FROM synced_files"
        )
        return [
            {"path": r[0], "hash": r[1], "mtime": r[2], "size": r[3], "ragflow_doc_id": r[4], "synced_at": r[5]}
            for r in cur.fetchall()
        ]
    
    def upsert_file(self, info: FileInfo, ragflow_doc_id: str | None = None):
        """Insert or update a synced file record."""
        self.conn.execute("""
            INSERT OR REPLACE INTO synced_files (path, hash, mtime, size, ragflow_doc_id, synced_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (info.path, info.hash, info.mtime, info.size, ragflow_doc_id, datetime.utcnow().isoformat()))
        self.conn.commit()
    
    def delete_file(self, path: str):
        """Remove a file from sync tracking."""
        self.conn.execute("DELETE FROM synced_files WHERE path = ?", (path,))
        self.conn.commit()
    
    def clear_all(self):
        """Clear all sync records."""
        self.conn.execute("DELETE FROM synced_files")
        self.conn.commit()
    
    def get_stats(self) -> dict:
        """Get sync statistics."""
        cur = self.conn.execute("SELECT COUNT(*), SUM(size) FROM synced_files")
        row = cur.fetchone()
        return {"file_count": row[0] or 0, "total_size": row[1] or 0}


class RAGFlowSync:
    """Sync local documentation to RAGFlow."""
    
    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        dataset_id: str = DATASET_ID,
        project_root: Path = PROJECT_ROOT,
        state_db: Path = STATE_DB,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.dataset_id = dataset_id
        self.project_root = Path(project_root)
        self.db = SyncDatabase(state_db)
        self.timeout = 120
    
    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
    
    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make API request."""
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", self._headers)
        resp = requests.request(method, f"{self.api_url}{path}", **kwargs)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error: {data.get('message')}")
        return data.get("data", {})
    
    def _is_excluded(self, path: Path) -> bool:
        """Check if path matches any exclude pattern."""
        path_str = str(path)
        for excl in EXCLUDE_PATTERNS:
            # Simple glob matching
            if "**" in excl:
                # Convert glob to check
                parts = excl.split("**")
                if len(parts) == 2 and parts[0] == "" and parts[1].startswith("/"):
                    # Pattern like "**/node_modules/**"
                    check = parts[1][1:].rstrip("/**")
                    if f"/{check}/" in path_str or path_str.endswith(f"/{check}"):
                        return True
            elif path.match(excl):
                return True
        return False
    
    def get_local_files(self) -> dict[str, FileInfo]:
        """Scan all source directories for indexable files."""
        files = {}
        
        for rel_dir, patterns in SOURCE_DIRS:
            source_dir = self.project_root / rel_dir
            if not source_dir.exists():
                logger.warning(f"Source directory not found: {source_dir}")
                continue
            
            for pattern in patterns:
                for path in source_dir.rglob(pattern):
                    if self._is_excluded(path) or not path.is_file():
                        continue
                    
                    try:
                        info = FileInfo.from_path(path, self.project_root)
                        files[info.path] = info
                    except Exception as e:
                        logger.warning(f"Error reading {path}: {e}")
        
        return files
    
    def get_ragflow_docs(self) -> dict[str, str]:
        """Get all documents from RAGFlow dataset. Returns {name: id}."""
        docs = {}
        page = 1
        while True:
            data = self._request(
                "GET",
                f"/datasets/{self.dataset_id}/documents",
                params={"page": page, "page_size": 100}
            )
            for doc in data.get("docs", []):
                docs[doc["name"]] = doc["id"]
            if len(data.get("docs", [])) < 100:
                break
            page += 1
        return docs
    
    def upload_file(self, file_path: Path) -> str | None:
        """Upload a file to RAGFlow. Returns document ID.
        
        Note: RAGFlow doesn't support .tsx/.jsx extensions, so we rename
        them to .txt for upload while preserving the original path in tracking.
        """
        try:
            # Determine upload filename - RAGFlow doesn't support .tsx/.jsx
            upload_name = file_path.name
            content_type = "text/markdown"
            
            if file_path.suffix in ('.tsx', '.jsx'):
                # Rename to .txt for upload (preserves full original name)
                upload_name = file_path.name + ".txt"
                content_type = "text/plain"
            elif file_path.suffix == '.py':
                content_type = "text/x-python"
            elif file_path.suffix in ('.ts', '.js'):
                content_type = "text/javascript"
            
            with open(file_path, "rb") as f:
                files = [("file", (upload_name, f, content_type))]
                data = self._request(
                    "POST",
                    f"/datasets/{self.dataset_id}/documents",
                    files=files,
                    headers=self._headers,
                )
            # Get the document ID from response
            if isinstance(data, list) and data:
                return data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            return None
    
    def delete_docs(self, doc_ids: list[str]) -> int:
        """Delete documents by ID. Returns count deleted."""
        if not doc_ids:
            return 0
        try:
            self._request(
                "DELETE",
                f"/datasets/{self.dataset_id}/documents",
                json={"ids": doc_ids}
            )
            return len(doc_ids)
        except Exception as e:
            logger.error(f"Failed to delete docs: {e}")
            return 0
    
    def parse_docs(self, doc_ids: list[str]):
        """Trigger parsing for uploaded documents."""
        if not doc_ids:
            return
        try:
            # RAGFlow API uses /chunks endpoint to trigger parsing
            self._request(
                "POST",
                f"/datasets/{self.dataset_id}/chunks",
                json={"document_ids": doc_ids}
            )
        except Exception as e:
            logger.warning(f"Parse request failed: {e}")
    
    def compute_changes(self, full: bool = False) -> dict:
        """
        Compute what needs to be synced.
        
        Returns dict with:
            - to_upload: list of FileInfo for new/modified files
            - to_delete: list of paths for removed files
            - unchanged: count of unchanged files
        """
        local_files = self.get_local_files()
        synced = {f["path"]: f for f in self.db.get_all_synced()}
        
        to_upload = []
        to_delete = []
        unchanged = 0
        
        # Check local files
        for path, info in local_files.items():
            if full:
                # Full re-index: upload everything
                to_upload.append(info)
            elif path not in synced:
                # New file
                to_upload.append(info)
            elif synced[path]["hash"] != info.hash:
                # Modified file
                to_upload.append(info)
            else:
                unchanged += 1
        
        # Check for deleted files
        for path in synced:
            if path not in local_files:
                to_delete.append(path)
        
        return {
            "to_upload": to_upload,
            "to_delete": to_delete,
            "unchanged": unchanged,
            "total_local": len(local_files),
        }
    
    def sync(self, full: bool = False, dry_run: bool = False) -> dict:
        """
        Sync local docs to RAGFlow.
        
        Args:
            full: If True, delete all and re-upload everything
            dry_run: If True, only show what would happen
            
        Returns:
            Stats dict with counts
        """
        logger.info("Computing changes...")
        changes = self.compute_changes(full=full)
        
        stats = {
            "uploaded": 0,
            "deleted": 0,
            "unchanged": changes["unchanged"],
            "failed": 0,
        }
        
        logger.info(f"Local files: {changes['total_local']}")
        logger.info(f"To upload: {len(changes['to_upload'])}")
        logger.info(f"To delete: {len(changes['to_delete'])}")
        logger.info(f"Unchanged: {changes['unchanged']}")
        
        if dry_run:
            logger.info("\n[DRY RUN] Would upload:")
            for info in changes["to_upload"][:20]:
                logger.info(f"  + {info.path}")
            if len(changes["to_upload"]) > 20:
                logger.info(f"  ... and {len(changes['to_upload']) - 20} more")
            
            logger.info("\n[DRY RUN] Would delete:")
            for path in changes["to_delete"][:20]:
                logger.info(f"  - {path}")
            if len(changes["to_delete"]) > 20:
                logger.info(f"  ... and {len(changes['to_delete']) - 20} more")
            
            return stats
        
        # Handle full re-index
        if full:
            logger.info("Full re-index: clearing RAGFlow dataset and local state...")
            ragflow_docs = self.get_ragflow_docs()
            if ragflow_docs:
                self.delete_docs(list(ragflow_docs.values()))
            self.db.clear_all()
        
        # Delete removed files from RAGFlow
        if changes["to_delete"]:
            logger.info(f"Deleting {len(changes['to_delete'])} removed files...")
            for path in changes["to_delete"]:
                synced = self.db.get_synced_file(path)
                if synced and synced.get("ragflow_doc_id"):
                    self.delete_docs([synced["ragflow_doc_id"]])
                self.db.delete_file(path)
                stats["deleted"] += 1
        
        # Upload new/modified files
        if changes["to_upload"]:
            logger.info(f"Uploading {len(changes['to_upload'])} files...")
            doc_ids = []
            for i, info in enumerate(changes["to_upload"]):
                file_path = self.project_root / info.path
                doc_id = self.upload_file(file_path)
                if doc_id:
                    self.db.upsert_file(info, doc_id)
                    doc_ids.append(doc_id)
                    stats["uploaded"] += 1
                else:
                    stats["failed"] += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"  Progress: {i + 1}/{len(changes['to_upload'])}")
            
            # Trigger parsing
            if doc_ids:
                logger.info(f"Triggering parsing for {len(doc_ids)} documents...")
                # Parse in batches
                for i in range(0, len(doc_ids), 20):
                    batch = doc_ids[i:i+20]
                    self.parse_docs(batch)
        
        return stats
    
    def status(self) -> dict:
        """Get current sync status."""
        local_files = self.get_local_files()
        db_stats = self.db.get_stats()
        
        try:
            ragflow_docs = self.get_ragflow_docs()
            ragflow_count = len(ragflow_docs)
        except Exception:
            ragflow_count = -1
        
        return {
            "local_files": len(local_files),
            "synced_files": db_stats["file_count"],
            "ragflow_docs": ragflow_count,
            "total_size_mb": db_stats["total_size"] / (1024 * 1024),
        }
    
    def get_parsing_progress(self) -> dict:
        """Get parsing progress for all documents."""
        statuses = {}
        chunks = 0
        tokens = 0
        page = 1
        
        while True:
            data = self._request(
                "GET",
                f"/datasets/{self.dataset_id}/documents",
                params={"page": page, "page_size": 100}
            )
            docs = data.get("docs", [])
            if not docs:
                break
            for d in docs:
                run = d.get("run", "UNKNOWN")
                statuses[run] = statuses.get(run, 0) + 1
                chunks += d.get("chunk_count", 0)
                tokens += d.get("token_count", 0)
            page += 1
        
        total = sum(statuses.values())
        return {
            "statuses": statuses,
            "total": total,
            "chunks": chunks,
            "tokens": tokens,
        }


def main():
    parser = argparse.ArgumentParser(description="RAGFlow incremental sync for DSA-110 docs")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync documents to RAGFlow")
    sync_parser.add_argument("--full", action="store_true", help="Full re-index (delete all, upload fresh)")
    sync_parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    
    # status command
    subparsers.add_parser("status", help="Show sync status")
    
    # progress command
    subparsers.add_parser("progress", help="Show parsing progress")
    
    # clear command
    subparsers.add_parser("clear", help="Clear local sync state (doesn't affect RAGFlow)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    syncer = RAGFlowSync()
    
    if args.command == "sync":
        print("=" * 60)
        print("RAGFlow Incremental Sync")
        print("=" * 60)
        stats = syncer.sync(full=args.full, dry_run=args.dry_run)
        print("\nResults:")
        print(f"  Uploaded:  {stats['uploaded']}")
        print(f"  Deleted:   {stats['deleted']}")
        print(f"  Unchanged: {stats['unchanged']}")
        print(f"  Failed:    {stats['failed']}")
        
    elif args.command == "status":
        status = syncer.status()
        print("RAGFlow Sync Status")
        print("=" * 40)
        print(f"Local files:     {status['local_files']}")
        print(f"Synced (tracked): {status['synced_files']}")
        print(f"RAGFlow docs:    {status['ragflow_docs']}")
        print(f"Total size:      {status['total_size_mb']:.2f} MB")
    
    elif args.command == "progress":
        print("RAGFlow Parsing Progress")
        print("=" * 50)
        progress = syncer.get_parsing_progress()
        total = progress["total"]
        
        for status, count in sorted(progress["statuses"].items()):
            pct = 100 * count / total if total else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"  {status:10} {bar} {count:4} ({pct:.1f}%)")
        
        print(f"\nTotal: {total} documents")
        print(f"Chunks: {progress['chunks']:,}")
        print(f"Tokens: {progress['tokens']:,}")
        
    elif args.command == "clear":
        syncer.db.clear_all()
        print("Cleared local sync state")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
