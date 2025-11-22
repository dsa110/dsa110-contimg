"""Unit tests for transient intervention functions.

Tests the user intervention capabilities added in Phase 3.5:
- acknowledge_alert()
- classify_candidate()
- update_follow_up_status()
- add_notes()
"""

import sqlite3

# Import from the nested src structure
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "dsa110_contimg" / "src"))

from dsa110_contimg.catalog.transient_detection import (
    acknowledge_alert,
    add_notes,
    classify_candidate,
    create_transient_detection_tables,
    update_follow_up_status,
)


@pytest.fixture
def temp_db():
    """Create temporary database with transient tables."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name

    # Create tables
    create_transient_detection_tables(db_path)

    # Insert test data
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Insert test candidate
    cur.execute(
        """
        INSERT INTO transient_candidates 
        (source_name, ra_deg, dec_deg, detection_type, flux_obs_mjy, 
         significance_sigma, detected_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("TEST_SRC_001", 45.0, 30.0, "new_source", 10.5, 7.2, time.time(), time.time()),
    )

    # Insert test alert
    cur.execute(
        """
        INSERT INTO transient_alerts 
        (candidate_id, alert_level, alert_message, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (1, "HIGH", "New transient detected", time.time()),
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestAcknowledgeAlert:
    """Tests for acknowledge_alert() function."""

    def test_acknowledge_alert_success(self, temp_db):
        """Test successfully acknowledging an alert."""
        result = acknowledge_alert(
            alert_id=1,
            acknowledged_by="test_user",
            notes="Reviewed - false positive",
            db_path=temp_db,
        )

        assert result is True

        # Verify database update
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute(
            "SELECT acknowledged, acknowledged_by, notes FROM transient_alerts WHERE id = 1"
        )
        row = cur.fetchone()
        conn.close()

        assert row[0] == 1  # acknowledged
        assert row[1] == "test_user"
        assert "false positive" in row[2]

    def test_acknowledge_alert_no_notes(self, temp_db):
        """Test acknowledging without notes."""
        result = acknowledge_alert(alert_id=1, acknowledged_by="operator", db_path=temp_db)

        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT acknowledged, acknowledged_by FROM transient_alerts WHERE id = 1")
        row = cur.fetchone()
        conn.close()

        assert row[0] == 1
        assert row[1] == "operator"

    def test_acknowledge_alert_invalid_id(self, temp_db):
        """Test acknowledging non-existent alert raises ValueError."""
        with pytest.raises(ValueError, match="Alert ID 999 not found"):
            acknowledge_alert(alert_id=999, acknowledged_by="test_user", db_path=temp_db)

    def test_acknowledge_alert_append_notes(self, temp_db):
        """Test that multiple acknowledgments append notes."""
        # First acknowledgment
        acknowledge_alert(
            alert_id=1,
            acknowledged_by="user1",
            notes="First review",
            db_path=temp_db,
        )

        # Second acknowledgment (should append)
        acknowledge_alert(
            alert_id=1,
            acknowledged_by="user2",
            notes="Second review",
            db_path=temp_db,
        )

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT notes FROM transient_alerts WHERE id = 1")
        notes = cur.fetchone()[0]
        conn.close()

        assert "First review" in notes
        assert "Second review" in notes


class TestClassifyCandidate:
    """Tests for classify_candidate() function."""

    def test_classify_candidate_success(self, temp_db):
        """Test successfully classifying a candidate."""
        result = classify_candidate(
            candidate_id=1,
            classification="real",
            classified_by="astronomer",
            notes="Confirmed with follow-up",
            db_path=temp_db,
        )

        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT classification, notes FROM transient_candidates WHERE id = 1")
        row = cur.fetchone()
        conn.close()

        assert row[0] == "real"
        assert "Confirmed with follow-up" in row[1]
        assert "astronomer" in row[1]

    def test_classify_candidate_all_valid_types(self, temp_db):
        """Test all valid classification types."""
        valid_types = ["real", "artifact", "variable", "uncertain"]

        for idx, classification in enumerate(valid_types, start=1):
            # Re-classify the same candidate
            result = classify_candidate(
                candidate_id=1,
                classification=classification,
                classified_by="test_user",
                db_path=temp_db,
            )
            assert result is True

    def test_classify_candidate_invalid_type(self, temp_db):
        """Test invalid classification raises ValueError."""
        with pytest.raises(ValueError, match="Invalid classification 'bogus'"):
            classify_candidate(
                candidate_id=1,
                classification="bogus",
                classified_by="test_user",
                db_path=temp_db,
            )

    def test_classify_candidate_invalid_id(self, temp_db):
        """Test classifying non-existent candidate raises ValueError."""
        with pytest.raises(ValueError, match="Candidate ID 999 not found"):
            classify_candidate(
                candidate_id=999,
                classification="real",
                classified_by="test_user",
                db_path=temp_db,
            )

    def test_classify_candidate_case_insensitive(self, temp_db):
        """Test classification is case-insensitive."""
        result = classify_candidate(
            candidate_id=1,
            classification="REAL",
            classified_by="test_user",
            db_path=temp_db,
        )

        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT classification FROM transient_candidates WHERE id = 1")
        classification = cur.fetchone()[0]
        conn.close()

        assert classification == "real"  # Stored as lowercase


class TestUpdateFollowUpStatus:
    """Tests for update_follow_up_status() function."""

    def test_update_alert_status(self, temp_db):
        """Test updating follow-up status for an alert."""
        result = update_follow_up_status(
            item_id=1,
            item_type="alert",
            status="scheduled",
            notes="VLA observation scheduled",
            db_path=temp_db,
        )

        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT follow_up_status, notes FROM transient_alerts WHERE id = 1")
        row = cur.fetchone()
        conn.close()

        assert row[0] == "scheduled"
        assert "VLA observation scheduled" in row[1]

    def test_update_candidate_status(self, temp_db):
        """Test updating follow-up status for a candidate."""
        result = update_follow_up_status(
            item_id=1,
            item_type="candidate",
            status="completed",
            notes="Follow-up completed",
            db_path=temp_db,
        )

        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT follow_up_status FROM transient_candidates WHERE id = 1")
        status = cur.fetchone()[0]
        conn.close()

        assert status == "completed"

    def test_update_status_all_valid_statuses(self, temp_db):
        """Test all valid status values."""
        valid_statuses = ["pending", "scheduled", "completed", "declined"]

        for status in valid_statuses:
            result = update_follow_up_status(
                item_id=1,
                item_type="alert",
                status=status,
                db_path=temp_db,
            )
            assert result is True

    def test_update_status_invalid_status(self, temp_db):
        """Test invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status 'bogus'"):
            update_follow_up_status(
                item_id=1,
                item_type="alert",
                status="bogus",
                db_path=temp_db,
            )

    def test_update_status_invalid_type(self, temp_db):
        """Test invalid item_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid item_type 'bogus'"):
            update_follow_up_status(
                item_id=1,
                item_type="bogus",
                status="pending",
                db_path=temp_db,
            )

    def test_update_status_invalid_id(self, temp_db):
        """Test invalid item_id raises ValueError."""
        with pytest.raises(ValueError, match="Alert ID 999 not found"):
            update_follow_up_status(
                item_id=999,
                item_type="alert",
                status="pending",
                db_path=temp_db,
            )


class TestAddNotes:
    """Tests for add_notes() function."""

    def test_add_notes_append(self, temp_db):
        """Test appending notes to existing notes."""
        # Add first note
        result = add_notes(
            item_id=1,
            item_type="candidate",
            notes="First observation",
            username="user1",
            append=True,
            db_path=temp_db,
        )
        assert result is True

        # Append second note
        result = add_notes(
            item_id=1,
            item_type="candidate",
            notes="Second observation",
            username="user2",
            append=True,
            db_path=temp_db,
        )
        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT notes FROM transient_candidates WHERE id = 1")
        notes = cur.fetchone()[0]
        conn.close()

        assert "First observation" in notes
        assert "Second observation" in notes
        assert "user1" in notes
        assert "user2" in notes

    def test_add_notes_replace(self, temp_db):
        """Test replacing notes."""
        # Add first note
        add_notes(
            item_id=1,
            item_type="alert",
            notes="First note",
            username="user1",
            db_path=temp_db,
        )

        # Replace with second note
        result = add_notes(
            item_id=1,
            item_type="alert",
            notes="Replacement note",
            username="user2",
            append=False,
            db_path=temp_db,
        )
        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT notes FROM transient_alerts WHERE id = 1")
        notes = cur.fetchone()[0]
        conn.close()

        assert "Replacement note" in notes
        assert "First note" not in notes

    def test_add_notes_alert(self, temp_db):
        """Test adding notes to an alert."""
        result = add_notes(
            item_id=1,
            item_type="alert",
            notes="Alert note",
            username="operator",
            db_path=temp_db,
        )

        assert result is True

        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT notes FROM transient_alerts WHERE id = 1")
        notes = cur.fetchone()[0]
        conn.close()

        assert "Alert note" in notes
        assert "operator" in notes

    def test_add_notes_invalid_type(self, temp_db):
        """Test invalid item_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid item_type 'bogus'"):
            add_notes(
                item_id=1,
                item_type="bogus",
                notes="Test note",
                username="user",
                db_path=temp_db,
            )

    def test_add_notes_invalid_id(self, temp_db):
        """Test invalid item_id raises ValueError."""
        with pytest.raises(ValueError, match="Candidate ID 999 not found"):
            add_notes(
                item_id=999,
                item_type="candidate",
                notes="Test note",
                username="user",
                db_path=temp_db,
            )
