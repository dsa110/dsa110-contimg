"""
Unit tests for images_insert helper function.

Verifies that images_insert correctly inserts records into the images table
with the expected type, created_at, pbcor, and other metadata fields.
"""

import time

import pytest

from dsa110_contimg.database.unified import (
    images_insert,
    init_unified_db,
)


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_images_insert.sqlite3"


@pytest.fixture
def db(temp_db_path):
    """Create and initialize a test database with schema."""
    database = init_unified_db(temp_db_path)
    # Insert a parent MS record for foreign key compliance
    database.execute(
        "INSERT INTO ms_index (path, mid_mjd, status, created_at) VALUES (?, ?, ?, ?)",
        ("/test/observation.ms", 60000.0, "completed", time.time()),
    )
    yield database
    database.close()


class TestImagesInsert:
    """Test images_insert helper function."""

    def test_basic_insert(self, db):
        """images_insert should insert a record with required fields."""
        now_ts = time.time()
        image_id = images_insert(
            db.conn,
            "/test/image.fits",
            "/test/observation.ms",
            "dirty",
            created_at=now_ts,
        )

        assert image_id is not None
        assert image_id > 0

        # Verify the record
        row = db.query_one("SELECT * FROM images WHERE id = ?", (image_id,))
        assert row is not None
        assert row["path"] == "/test/image.fits"
        assert row["ms_path"] == "/test/observation.ms"
        assert row["type"] == "dirty"
        assert abs(row["created_at"] - now_ts) < 1.0  # Within 1 second

    def test_insert_with_pbcor(self, db):
        """images_insert should correctly set pbcor field."""
        now_ts = time.time()

        # Insert image without pbcor (pbcor=0)
        id1 = images_insert(
            db.conn,
            "/test/image.image",
            "/test/observation.ms",
            "5min",
            created_at=now_ts,
            pbcor=0,
        )

        # Insert image with pbcor (pbcor=1)
        id2 = images_insert(
            db.conn,
            "/test/image.pbcor",
            "/test/observation.ms",
            "5min",
            created_at=now_ts,
            pbcor=1,
        )

        row1 = db.query_one("SELECT * FROM images WHERE id = ?", (id1,))
        row2 = db.query_one("SELECT * FROM images WHERE id = ?", (id2,))

        assert row1["pbcor"] == 0
        assert row2["pbcor"] == 1

    def test_insert_with_all_metadata(self, db):
        """images_insert should support all optional metadata fields."""
        now_ts = time.time()
        image_id = images_insert(
            db.conn,
            "/test/image.fits",
            "/test/observation.ms",
            "clean",
            created_at=now_ts,
            pbcor=1,
            noise_jy=0.001,
            center_ra_deg=180.0,
            center_dec_deg=45.0,
            beam_major_arcsec=5.0,
            beam_minor_arcsec=3.0,
            beam_pa_deg=30.0,
            dynamic_range=1000.0,
            field_name="3C286",
            imsize_x=1024,
            imsize_y=1024,
            cellsize_arcsec=2.5,
            freq_ghz=1.4,
            bandwidth_mhz=256.0,
            integration_sec=300.0,
        )

        row = db.query_one("SELECT * FROM images WHERE id = ?", (image_id,))

        assert row["type"] == "clean"
        assert row["pbcor"] == 1
        assert abs(row["noise_jy"] - 0.001) < 1e-9
        assert abs(row["center_ra_deg"] - 180.0) < 1e-6
        assert abs(row["center_dec_deg"] - 45.0) < 1e-6
        assert abs(row["beam_major_arcsec"] - 5.0) < 1e-6
        assert abs(row["beam_minor_arcsec"] - 3.0) < 1e-6
        assert abs(row["beam_pa_deg"] - 30.0) < 1e-6
        assert row["field_name"] == "3C286"
        assert row["imsize_x"] == 1024
        assert row["imsize_y"] == 1024
        assert abs(row["cellsize_arcsec"] - 2.5) < 1e-6
        assert abs(row["freq_ghz"] - 1.4) < 1e-6
        assert abs(row["bandwidth_mhz"] - 256.0) < 1e-6
        assert abs(row["integration_sec"] - 300.0) < 1e-6

    def test_insert_defaults_created_at(self, db):
        """images_insert should default created_at to current time if not specified."""
        before = time.time()
        image_id = images_insert(
            db.conn,
            "/test/image2.fits",
            "/test/observation.ms",
            "residual",
        )
        after = time.time()

        row = db.query_one("SELECT created_at FROM images WHERE id = ?", (image_id,))
        assert before <= row["created_at"] <= after

    def test_insert_or_replace_behavior(self, db):
        """images_insert should replace existing record with same path."""
        now_ts = time.time()

        # First insert
        _id1 = images_insert(
            db.conn,
            "/test/same_path.fits",
            "/test/observation.ms",
            "dirty",
            created_at=now_ts,
            noise_jy=0.002,
        )

        # Second insert with same path but different metadata
        _id2 = images_insert(
            db.conn,
            "/test/same_path.fits",
            "/test/observation.ms",
            "clean",
            created_at=now_ts + 100,
            noise_jy=0.001,
        )

        # Should only have one record (replaced)
        count = db.query_val("SELECT COUNT(*) FROM images WHERE path = ?", ("/test/same_path.fits",))
        assert count == 1

        # Should have the updated values
        row = db.query_one("SELECT * FROM images WHERE path = ?", ("/test/same_path.fits",))
        assert row["type"] == "clean"
        assert abs(row["noise_jy"] - 0.001) < 1e-9

    def test_streaming_converter_pattern(self, db):
        """Test the exact pattern used by streaming_converter after fix.

        This verifies that the fixed call-site pattern:
            images_insert(conn, p, ms_path, "5min", created_at=now_ts, pbcor=pbcor)
        correctly inserts records with proper field mapping.
        """
        ms_path = "/test/observation.ms"
        now_ts = time.time()

        # Simulate the streaming converter's image insertion pattern
        suffixes_and_pbcor = [
            (".image", 0),
            (".pb", 0),
            (".pbcor", 1),
            (".residual", 0),
            (".model", 0),
        ]

        imgroot = "/stage/images/2025-01-01T12:00:00"
        for suffix, pbcor_val in suffixes_and_pbcor:
            p = f"{imgroot}{suffix}"
            # This is the FIXED pattern from streaming_converter
            images_insert(
                db.conn,
                p,
                ms_path,
                "5min",  # image_type
                created_at=now_ts,
                pbcor=pbcor_val,
            )

        # Verify all records were inserted correctly
        rows = db.query(
            "SELECT path, ms_path, type, pbcor FROM images ORDER BY path"
        )
        assert len(rows) == 5

        # Check each record has correct type and pbcor
        for row in rows:
            assert row["type"] == "5min"
            assert row["ms_path"] == ms_path
            if ".pbcor" in row["path"]:
                assert row["pbcor"] == 1
            else:
                assert row["pbcor"] == 0

    def test_wrong_positional_args_would_fail(self, db):
        """Demonstrate what happens with wrong positional argument order.

        The OLD (buggy) pattern was:
            images_insert(conn, p, ms_path, now_ts, "5min", pbcor)

        This would pass `now_ts` (a float timestamp) as `image_type` (a string),
        and "5min" and pbcor as unexpected positional args to **kwargs.

        This test documents the expected behavior with correct args.
        """
        ms_path = "/test/observation.ms"
        now_ts = time.time()

        # CORRECT: Use keyword args for clarity and safety
        image_id = images_insert(
            db.conn,
            "/test/correct.fits",
            ms_path,
            "5min",  # image_type as 3rd positional arg (correct)
            created_at=now_ts,
            pbcor=1,
        )

        row = db.query_one("SELECT * FROM images WHERE id = ?", (image_id,))
        assert row["type"] == "5min"
        assert row["pbcor"] == 1
        assert abs(row["created_at"] - now_ts) < 1.0


class TestImagesInsertEdgeCases:
    """Test edge cases and error handling for images_insert."""

    def test_null_optional_fields(self, db):
        """images_insert should allow NULL for optional metadata fields."""
        image_id = images_insert(
            db.conn,
            "/test/minimal.fits",
            "/test/observation.ms",
            "dirty",
        )

        row = db.query_one("SELECT * FROM images WHERE id = ?", (image_id,))

        # Optional fields should be NULL
        assert row["noise_jy"] is None
        assert row["center_ra_deg"] is None
        assert row["center_dec_deg"] is None
        assert row["beam_major_arcsec"] is None

    def test_very_small_noise_value(self, db):
        """images_insert should handle very small noise values."""
        image_id = images_insert(
            db.conn,
            "/test/lownoise.fits",
            "/test/observation.ms",
            "clean",
            noise_jy=1e-9,
        )

        row = db.query_one("SELECT noise_jy FROM images WHERE id = ?", (image_id,))
        assert abs(row["noise_jy"] - 1e-9) < 1e-15

    def test_unicode_field_name(self, db):
        """images_insert should handle unicode in field_name."""
        image_id = images_insert(
            db.conn,
            "/test/unicode.fits",
            "/test/observation.ms",
            "dirty",
            field_name="Cygnus A (α=299.868°)",
        )

        row = db.query_one("SELECT field_name FROM images WHERE id = ?", (image_id,))
        assert row["field_name"] == "Cygnus A (α=299.868°)"
