#!/usr/bin/env python3
"""Tests for streaming config defaults returned by GET /api/streaming/config."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


@pytest.mark.unit
def test_streaming_config_get_uses_env_defaults(monkeypatch):
    """Without a saved config, the endpoint should return env-derived defaults."""
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONTIMG_INPUT_DIR", "/custom/incoming")
    monkeypatch.setenv("CONTIMG_OUTPUT_DIR", "/custom/output")
    monkeypatch.setenv("CONTIMG_QUEUE_DB", "/custom/ingest.sqlite3")
    monkeypatch.setenv("CONTIMG_REGISTRY_DB", "/custom/cal_registry.sqlite3")
    monkeypatch.setenv("CONTIMG_SCRATCH_DIR", "/custom/scratch")

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/streaming/config")
    assert response.status_code == 200
    data = response.json()
    assert data["input_dir"] == "/custom/incoming"
    assert data["output_dir"] == "/custom/output"
    assert data["queue_db"] == "/custom/ingest.sqlite3"
    assert data["registry_db"] == "/custom/cal_registry.sqlite3"
    assert data["scratch_dir"] == "/custom/scratch"
