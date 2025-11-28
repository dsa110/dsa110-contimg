#!/usr/bin/env python3
"""Validation-path tests for streaming config endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


@pytest.mark.unit
def test_streaming_config_validation_error_in_dev(tmp_path, monkeypatch):
    """DEV mode: test_validation_error should raise a 422 with structured errors."""
    monkeypatch.setenv("PIPELINE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "dev")

    app = create_app()
    client = TestClient(app)

    payload = {
        "input_dir": "/data/incoming",
        "output_dir": "/data/dsa110-contimg/ms",
    }
    response = client.post("/api/streaming/config?test_validation_error=true", json=payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    assert "errors" in detail
    fields = {err["field"] for err in detail["errors"]}
    assert {"input_dir", "max_workers"} & fields  # expect at least these from route stub


@pytest.mark.unit
def test_streaming_config_validation_noop_in_production(tmp_path, monkeypatch):
    """Production mode should ignore test_validation_error and accept the payload."""
    monkeypatch.setenv("PIPELINE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "production")

    app = create_app()
    client = TestClient(app)

    payload = {
        "input_dir": "/data/incoming",
        "output_dir": "/data/dsa110-contimg/ms",
    }
    response = client.post("/api/streaming/config?test_validation_error=true", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Configuration updated" in data["message"]
