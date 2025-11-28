#!/usr/bin/env python3
"""Tests for streaming config update path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


@pytest.mark.unit
def test_streaming_config_updates_file(tmp_path, monkeypatch):
    """Posting a streaming config should succeed and persist the config file."""
    monkeypatch.setenv("PIPELINE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "dev")

    app = create_app()
    client = TestClient(app)

    payload = {
        "input_dir": "/data/incoming",
        "output_dir": "/data/dsa110-contimg/ms",
        "queue_db": "/data/dsa110-contimg/state/ingest.sqlite3",
        "registry_db": "/data/dsa110-contimg/state/cal_registry.sqlite3",
        "scratch_dir": "/data/dsa110-contimg/state",
        "expected_subbands": 8,
        "log_level": "INFO",
        "monitoring": False,
    }

    response = client.post("/api/streaming/config", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Configuration updated" in body["message"]

    config_file = tmp_path / "streaming_config.json"
    assert config_file.exists(), "Streaming config should be saved to state dir"
    on_disk = json.loads(config_file.read_text())
    assert on_disk["output_dir"] == payload["output_dir"]
    assert on_disk["queue_db"] == payload["queue_db"]
