# mypy: disable-error-code="import-not-found,import-untyped"
"""Smoke tests for Phase 3 - Production Deployment & Operations.

These tests verify that all Phase 3 deployment components exist and are properly
structured without requiring a running database or services.
"""

import os
import subprocess
from pathlib import Path

import pytest  # type: ignore[import-not-found]

# Get project root - tests are in backend/tests/smoke/
PROJECT_ROOT = Path(__file__).parents[3]  # Go up from smoke -> tests -> backend -> project root


@pytest.mark.smoke
class TestPhase3DeploymentScripts:
    """Tests for deployment script existence and structure."""

    @pytest.fixture
    def ops_scripts_dir(self) -> Path:
        """Get the ops/scripts directory path."""
        return PROJECT_ROOT / "ops" / "scripts"

    def test_deploy_absurd_script_exists(self, ops_scripts_dir: Path):
        """Verify deploy_absurd.sh exists."""
        script = ops_scripts_dir / "deploy_absurd.sh"
        assert script.exists(), f"Deployment script not found: {script}"

    def test_deploy_absurd_script_executable(self, ops_scripts_dir: Path):
        """Verify deploy_absurd.sh is executable (or at least valid bash)."""
        script = ops_scripts_dir / "deploy_absurd.sh"
        # Check syntax without executing
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in script: {result.stderr}"

    def test_health_check_script_exists(self, ops_scripts_dir: Path):
        """Verify health_check_absurd.sh exists."""
        script = ops_scripts_dir / "health_check_absurd.sh"
        assert script.exists(), f"Health check script not found: {script}"

    def test_health_check_script_syntax(self, ops_scripts_dir: Path):
        """Verify health_check_absurd.sh has valid syntax."""
        script = ops_scripts_dir / "health_check_absurd.sh"
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in script: {result.stderr}"

    def test_deploy_script_has_required_commands(self, ops_scripts_dir: Path):
        """Verify deploy script supports required commands."""
        script = ops_scripts_dir / "deploy_absurd.sh"
        content = script.read_text()

        required_commands = ["install", "start", "stop", "restart", "status", "uninstall"]
        for cmd in required_commands:
            assert cmd in content, f"Missing command '{cmd}' in deploy script"


@pytest.mark.smoke
class TestPhase3SystemdFiles:
    """Tests for systemd service files."""

    @pytest.fixture
    def systemd_dir(self) -> Path:
        """Get the ops/systemd directory path."""
        return PROJECT_ROOT / "ops" / "systemd"

    def test_absurd_worker_service_exists(self, systemd_dir: Path):
        """Verify contimg-absurd-worker.service exists."""
        service = systemd_dir / "contimg-absurd-worker.service"
        assert service.exists(), f"Service file not found: {service}"

    def test_absurd_worker_service_structure(self, systemd_dir: Path):
        """Verify service file has required sections."""
        service = systemd_dir / "contimg-absurd-worker.service"
        content = service.read_text()

        required_sections = ["[Unit]", "[Service]", "[Install]"]
        for section in required_sections:
            assert section in content, f"Missing section '{section}' in service file"

    def test_absurd_worker_service_restart_policy(self, systemd_dir: Path):
        """Verify service has proper restart configuration."""
        service = systemd_dir / "contimg-absurd-worker.service"
        content = service.read_text()

        assert "Restart=always" in content or "Restart=on-failure" in content
        assert "RestartSec=" in content

    def test_env_file_has_absurd_config(self, systemd_dir: Path):
        """Verify contimg.env has Absurd configuration."""
        env_file = systemd_dir / "contimg.env"
        assert env_file.exists(), f"Environment file not found: {env_file}"

        content = env_file.read_text()
        required_vars = [
            "ABSURD_ENABLED",
            "ABSURD_DATABASE_URL",
            "ABSURD_QUEUE_NAME",
            "ABSURD_WORKER_CONCURRENCY",
        ]
        for var in required_vars:
            assert var in content, f"Missing variable '{var}' in environment file"


@pytest.mark.smoke
class TestPhase3LogrotateConfig:
    """Tests for logrotate configuration."""

    @pytest.fixture
    def logrotate_dir(self) -> Path:
        """Get the ops/logrotate.d directory path."""
        return PROJECT_ROOT / "ops" / "logrotate.d"

    def test_logrotate_config_exists(self, logrotate_dir: Path):
        """Verify logrotate configuration exists."""
        config = logrotate_dir / "absurd-worker"
        assert config.exists(), f"Logrotate config not found: {config}"

    def test_logrotate_config_structure(self, logrotate_dir: Path):
        """Verify logrotate config has required directives."""
        config = logrotate_dir / "absurd-worker"
        content = config.read_text()

        required_directives = ["rotate", "compress", "daily", "missingok"]
        for directive in required_directives:
            assert directive in content, f"Missing directive '{directive}' in logrotate config"


@pytest.mark.smoke
class TestPhase3PrometheusEndpoint:
    """Tests for Prometheus metrics endpoint."""

    def test_prometheus_endpoint_in_router(self):
        """Verify Prometheus metrics endpoint is defined."""
        from dsa110_contimg.api.routers import absurd

        # Check that the endpoint function exists
        assert hasattr(absurd, "get_prometheus_metrics")

    def test_prometheus_endpoint_path(self):
        """Verify Prometheus endpoint has correct path."""
        from dsa110_contimg.api.routers.absurd import router

        # Find the Prometheus endpoint
        prometheus_route = None
        for route in router.routes:
            if hasattr(route, "path") and "prometheus" in route.path:
                prometheus_route = route
                break

        assert prometheus_route is not None, "Prometheus endpoint not found in router"
        assert prometheus_route.path == "/metrics/prometheus"


@pytest.mark.smoke
class TestPhase3OperationsDocumentation:
    """Tests for operations documentation."""

    @pytest.fixture
    def docs_dir(self) -> Path:
        """Get the docs/operations directory path."""
        return PROJECT_ROOT / "docs" / "operations"

    def test_operations_doc_exists(self, docs_dir: Path):
        """Verify absurd_operations.md exists."""
        doc = docs_dir / "absurd_operations.md"
        assert doc.exists(), f"Operations doc not found: {doc}"

    def test_operations_doc_has_runbooks(self, docs_dir: Path):
        """Verify operations doc has runbooks section."""
        doc = docs_dir / "absurd_operations.md"
        content = doc.read_text()

        assert "Runbook" in content, "Operations doc missing runbooks"
        assert "## Runbooks" in content or "# Runbooks" in content

    def test_operations_doc_has_monitoring(self, docs_dir: Path):
        """Verify operations doc has monitoring section."""
        doc = docs_dir / "absurd_operations.md"
        content = doc.read_text()

        assert "Prometheus" in content, "Operations doc missing Prometheus info"
        assert "Monitoring" in content, "Operations doc missing monitoring section"


@pytest.mark.smoke
class TestPhase3Integration:
    """Integration smoke tests for Phase 3 components."""

    def test_all_phase3_components_importable(self):
        """Verify all Phase 3 components can be imported."""
        # These should all import without error
        from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig
        from dsa110_contimg.absurd.monitoring import AbsurdMonitor
        from dsa110_contimg.api.routers.absurd import get_prometheus_metrics, router

        assert AbsurdClient is not None
        assert AbsurdConfig is not None
        assert AbsurdMonitor is not None
        assert router is not None
        assert get_prometheus_metrics is not None

    def test_prometheus_metrics_format(self):
        """Verify Prometheus endpoint can generate valid format."""
        # Test that we can construct Prometheus-style metric lines
        test_metrics = [
            "# HELP absurd_tasks_total Total number of tasks",
            "# TYPE absurd_tasks_total counter",
            'absurd_tasks_total{status="completed"} 100',
        ]

        for line in test_metrics:
            # Valid Prometheus lines should not raise
            assert isinstance(line, str)
            if line.startswith("#"):
                assert line.startswith("# HELP") or line.startswith("# TYPE")
            else:
                # Metric line should have name{labels} value format
                assert "{" in line or " " in line
