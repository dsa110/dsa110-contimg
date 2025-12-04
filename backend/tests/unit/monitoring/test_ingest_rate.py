"""
Unit tests for ingest rate metrics (Issue #12: Observability).

Tests the IngestRateMetrics dataclass and PipelineMetricsCollector
methods for tracking incoming vs processed data rates.
"""

from __future__ import annotations

import time

from dsa110_contimg.monitoring.pipeline_metrics import (
    IngestRateMetrics,
    PipelineMetricsCollector,
)


class TestIngestRateMetricsDataclass:
    """Tests for the IngestRateMetrics dataclass."""

    def test_rate_ratio_calculation(self):
        """Test rate ratio when processing faster than arrival."""
        metrics = IngestRateMetrics(
            groups_arrived=10,
            groups_per_hour=10.0,
            groups_processed=12,
            processed_per_hour=12.0,
        )
        assert metrics.rate_ratio == 1.2
        assert metrics.is_keeping_up is True

    def test_rate_ratio_falling_behind(self):
        """Test rate ratio when processing slower than arrival."""
        metrics = IngestRateMetrics(
            groups_arrived=10,
            groups_per_hour=10.0,
            groups_processed=5,
            processed_per_hour=5.0,
        )
        assert metrics.rate_ratio == 0.5
        assert metrics.is_keeping_up is False

    def test_rate_ratio_no_arrivals(self):
        """Test rate ratio when no data arriving (infinite capacity)."""
        metrics = IngestRateMetrics(
            groups_arrived=0,
            groups_per_hour=0.0,
            groups_processed=5,
            processed_per_hour=5.0,
        )
        assert metrics.rate_ratio == float("inf")
        assert metrics.is_keeping_up is True

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all relevant metrics."""
        metrics = IngestRateMetrics(
            groups_arrived=8,
            groups_per_hour=8.0,
            groups_processed=10,
            processed_per_hour=10.0,
            backlog_groups=2,
            backlog_growing=True,
            time_window_hours=1.0,
        )
        result = metrics.to_dict()

        assert "groups_arrived" in result
        assert "groups_per_hour" in result
        assert "groups_processed" in result
        assert "processed_per_hour" in result
        assert "backlog_groups" in result
        assert "backlog_growing" in result
        assert "rate_ratio" in result
        assert "is_keeping_up" in result
        assert "time_window_hours" in result

    def test_to_dict_handles_infinite_rate(self):
        """Test that to_dict handles infinite rate ratio gracefully."""
        metrics = IngestRateMetrics(
            groups_arrived=0,
            groups_per_hour=0.0,
        )
        result = metrics.to_dict()
        assert result["rate_ratio"] is None  # Infinite converted to None


class TestPipelineMetricsCollectorIngest:
    """Tests for ingest tracking in PipelineMetricsCollector."""

    def test_record_ingest_adds_timestamp(self):
        """Test that record_ingest adds arrival timestamps."""
        collector = PipelineMetricsCollector()

        collector.record_ingest("group_001")
        collector.record_ingest("group_002")

        # Check internal state
        assert len(collector._ingest_timestamps) == 2

    def test_get_ingest_rate_empty_collector(self):
        """Test get_ingest_rate with no data."""
        collector = PipelineMetricsCollector()

        metrics = collector.get_ingest_rate(hours=1.0)

        assert metrics.groups_arrived == 0
        assert metrics.groups_per_hour == 0.0
        assert metrics.backlog_groups == 0
        assert metrics.is_keeping_up is True

    def test_get_ingest_rate_with_arrivals(self):
        """Test get_ingest_rate with incoming data."""
        collector = PipelineMetricsCollector()

        # Record some arrivals
        for i in range(5):
            collector.record_ingest(f"group_{i:03d}")

        metrics = collector.get_ingest_rate(hours=1.0)

        assert metrics.groups_arrived == 5
        assert metrics.groups_per_hour == 5.0
        assert metrics.backlog_groups == 5  # Nothing processed yet

    def test_get_ingest_rate_with_processing(self):
        """Test get_ingest_rate when processing is happening."""
        collector = PipelineMetricsCollector()

        # Record some arrivals
        for i in range(5):
            collector.record_ingest(f"group_{i:03d}")

        # Simulate processing (add throughput timestamps)
        for i in range(3):
            collector._throughput_timestamps.append((time.time(), 1000))

        metrics = collector.get_ingest_rate(hours=1.0)

        assert metrics.groups_arrived == 5
        assert metrics.groups_processed == 3
        assert metrics.backlog_groups == 2

    def test_backlog_growing_detection(self):
        """Test detection of growing backlog."""
        collector = PipelineMetricsCollector()

        # First check - no backlog
        metrics1 = collector.get_ingest_rate(hours=1.0)
        assert metrics1.backlog_growing is False

        # Add arrivals without processing
        for i in range(5):
            collector.record_ingest(f"group_{i:03d}")

        # Second check - backlog growing
        metrics2 = collector.get_ingest_rate(hours=1.0)
        assert metrics2.backlog_growing is True

        # Third check with same backlog - should not be "growing"
        metrics3 = collector.get_ingest_rate(hours=1.0)
        assert metrics3.backlog_growing is False

    def test_get_summary_includes_ingest_rate(self):
        """Test that get_summary includes ingest rate metrics."""
        collector = PipelineMetricsCollector()

        # Add some data
        collector.record_ingest("group_001")

        summary = collector.get_summary(hours=1.0)

        assert "ingest_rate" in summary
        assert summary["ingest_rate"]["groups_arrived"] == 1


class TestThroughputAlertRules:
    """Tests for throughput-based alert rules."""

    def test_backlog_growing_alert_fires(self):
        """Test that backlog alert fires when threshold exceeded."""
        from dsa110_contimg.monitoring.alerting import create_throughput_alert_rules

        collector = PipelineMetricsCollector()

        # Add arrivals to exceed threshold
        for i in range(15):
            collector.record_ingest(f"group_{i:03d}")

        rules = create_throughput_alert_rules(
            collector,
            backlog_threshold=10,
        )

        # Find backlog growing rule
        backlog_rule = next(r for r in rules if r.name == "pipeline_backlog_growing")

        # First evaluation - backlog growing
        assert backlog_rule.condition() is True

    def test_backlog_alert_not_fired_below_threshold(self):
        """Test that backlog alert does not fire below threshold."""
        from dsa110_contimg.monitoring.alerting import create_throughput_alert_rules

        collector = PipelineMetricsCollector()

        # Add arrivals below threshold
        for i in range(5):
            collector.record_ingest(f"group_{i:03d}")

        rules = create_throughput_alert_rules(
            collector,
            backlog_threshold=10,
        )

        backlog_rule = next(r for r in rules if r.name == "pipeline_backlog_growing")
        assert backlog_rule.condition() is False

    def test_processing_slow_alert(self):
        """Test alert for slow processing rate."""
        from dsa110_contimg.monitoring.alerting import create_throughput_alert_rules

        collector = PipelineMetricsCollector()

        # Simulate more arrivals than processing
        for i in range(10):
            collector.record_ingest(f"group_{i:03d}")

        # Only process a few
        for i in range(3):
            collector._throughput_timestamps.append((time.time(), 1000))

        rules = create_throughput_alert_rules(
            collector,
            rate_threshold=0.8,
        )

        slow_rule = next(r for r in rules if r.name == "pipeline_processing_slow")
        # Rate is 3/10 = 0.3, which is below 0.8 threshold
        assert slow_rule.condition() is True
