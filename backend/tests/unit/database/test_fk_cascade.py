"""
Unit tests for database foreign key CASCADE behavior (Issue #14).

Tests that ON DELETE CASCADE policies properly clean up
related records when parent records are deleted.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


class TestForeignKeyCascade:
    """Tests for ON DELETE CASCADE behavior."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> Path:
        """Create a test database with the proper schema."""
        db_file = tmp_path / "test_cascade.sqlite3"
        conn = sqlite3.connect(db_file)

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Create ms_index table
        conn.execute("""
            CREATE TABLE ms_index (
                path TEXT PRIMARY KEY,
                status TEXT,
                stage TEXT
            )
        """)

        # Create images table with CASCADE
        conn.execute("""
            CREATE TABLE images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                ms_path TEXT NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY (ms_path) REFERENCES ms_index(path) ON DELETE CASCADE
            )
        """)

        # Create photometry table with CASCADE
        conn.execute("""
            CREATE TABLE photometry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                source_id TEXT NOT NULL,
                flux_jy REAL NOT NULL,
                FOREIGN KEY (image_path) REFERENCES images(path) ON DELETE CASCADE
            )
        """)

        conn.commit()
        conn.close()
        return db_file

    def test_delete_ms_cascades_to_images(self, db_path: Path):
        """Test that deleting an MS deletes related images."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Insert MS and images
        conn.execute("INSERT INTO ms_index (path, status) VALUES ('/test/ms1.ms', 'ready')")
        conn.execute("INSERT INTO images (path, ms_path, type) VALUES ('/test/img1.fits', '/test/ms1.ms', 'continuum')")
        conn.execute("INSERT INTO images (path, ms_path, type) VALUES ('/test/img2.fits', '/test/ms1.ms', 'dirty')")
        conn.commit()

        # Verify images exist
        count = conn.execute("SELECT COUNT(*) FROM images WHERE ms_path = '/test/ms1.ms'").fetchone()[0]
        assert count == 2

        # Delete MS
        conn.execute("DELETE FROM ms_index WHERE path = '/test/ms1.ms'")
        conn.commit()

        # Verify images are deleted
        count = conn.execute("SELECT COUNT(*) FROM images WHERE ms_path = '/test/ms1.ms'").fetchone()[0]
        assert count == 0

        conn.close()

    def test_delete_image_cascades_to_photometry(self, db_path: Path):
        """Test that deleting an image deletes related photometry."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Insert MS, image, and photometry
        conn.execute("INSERT INTO ms_index (path, status) VALUES ('/test/ms1.ms', 'ready')")
        conn.execute("INSERT INTO images (path, ms_path, type) VALUES ('/test/img1.fits', '/test/ms1.ms', 'continuum')")
        conn.execute("INSERT INTO photometry (image_path, source_id, flux_jy) VALUES ('/test/img1.fits', 'src1', 0.1)")
        conn.execute("INSERT INTO photometry (image_path, source_id, flux_jy) VALUES ('/test/img1.fits', 'src2', 0.2)")
        conn.commit()

        # Verify photometry exists
        count = conn.execute("SELECT COUNT(*) FROM photometry").fetchone()[0]
        assert count == 2

        # Delete image
        conn.execute("DELETE FROM images WHERE path = '/test/img1.fits'")
        conn.commit()

        # Verify photometry is deleted
        count = conn.execute("SELECT COUNT(*) FROM photometry").fetchone()[0]
        assert count == 0

        conn.close()

    def test_delete_ms_cascades_through_images_to_photometry(self, db_path: Path):
        """Test full cascade: MS -> images -> photometry."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Insert MS, image, and photometry
        conn.execute("INSERT INTO ms_index (path, status) VALUES ('/test/ms1.ms', 'ready')")
        conn.execute("INSERT INTO images (path, ms_path, type) VALUES ('/test/img1.fits', '/test/ms1.ms', 'continuum')")
        conn.execute("INSERT INTO photometry (image_path, source_id, flux_jy) VALUES ('/test/img1.fits', 'src1', 0.1)")
        conn.commit()

        # Verify all records exist
        assert conn.execute("SELECT COUNT(*) FROM ms_index").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM photometry").fetchone()[0] == 1

        # Delete MS (should cascade through images to photometry)
        conn.execute("DELETE FROM ms_index WHERE path = '/test/ms1.ms'")
        conn.commit()

        # Verify all related records are deleted
        assert conn.execute("SELECT COUNT(*) FROM ms_index").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM photometry").fetchone()[0] == 0

        conn.close()

    def test_other_ms_records_unaffected(self, db_path: Path):
        """Test that deleting one MS doesn't affect other MS records."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Insert two MS with images
        conn.execute("INSERT INTO ms_index (path, status) VALUES ('/test/ms1.ms', 'ready')")
        conn.execute("INSERT INTO ms_index (path, status) VALUES ('/test/ms2.ms', 'ready')")
        conn.execute("INSERT INTO images (path, ms_path, type) VALUES ('/test/img1.fits', '/test/ms1.ms', 'continuum')")
        conn.execute("INSERT INTO images (path, ms_path, type) VALUES ('/test/img2.fits', '/test/ms2.ms', 'continuum')")
        conn.commit()

        # Delete first MS
        conn.execute("DELETE FROM ms_index WHERE path = '/test/ms1.ms'")
        conn.commit()

        # Verify second MS and its image are unaffected
        assert conn.execute("SELECT COUNT(*) FROM ms_index").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 1
        assert conn.execute("SELECT path FROM images").fetchone()[0] == '/test/img2.fits'

        conn.close()

    def test_foreign_key_prevents_orphan_creation(self, db_path: Path):
        """Test that FK constraint prevents inserting orphan records."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Try to insert image without parent MS
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO images (path, ms_path, type) VALUES ('/test/orphan.fits', '/nonexistent/ms.ms', 'continuum')"
            )

        conn.close()
