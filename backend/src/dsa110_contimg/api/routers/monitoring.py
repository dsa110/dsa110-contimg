"""
API endpoints for operational monitoring visualizations.

Provides endpoints for:
- Performance monitoring (stage duration, throughput, failure rate)
- Antenna health monitoring (heatmaps, stability trends)
- Queue health monitoring (depth trends, processing rate, time-to-completion)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_default_paths() -> tuple[Path, Path]:
    """Get default database paths from environment or defaults."""
    queue_db = Path(os.getenv("DSA110_QUEUE_DB", "/data/dsa110-contimg/state/ingest.sqlite3"))
    products_db = Path(os.getenv("DSA110_PRODUCTS_DB", "/data/dsa110-contimg/state/products.sqlite3"))
    return queue_db, products_db


# ============================================================================
# Performance Monitoring Endpoints
# ============================================================================


@router.get("/performance/metrics")
def get_performance_metrics_data(
    hours: int = Query(24, description="Hours of history to fetch")
) -> Dict[str, Any]:
    """Get raw performance metrics data.

    Returns metrics from the performance_metrics table including:
    - Stage durations (load, phase, write)
    - Total processing time
    - Writer type

    Args:
        hours: Number of hours of history to fetch

    Returns:
        Dict with metrics list and summary statistics
    """
    from dsa110_contimg.qa.performance_monitoring import fetch_performance_metrics

    queue_db, _ = _get_default_paths()

    try:
        metrics = fetch_performance_metrics(queue_db, hours=hours)

        if not metrics:
            return {"metrics": [], "summary": {"count": 0, "error": "No metrics found"}}

        # Calculate summary statistics
        import numpy as np

        total_times = [m["total_time"] for m in metrics if m.get("total_time")]
        load_times = [m["load_time"] for m in metrics if m.get("load_time")]
        write_times = [m["write_time"] for m in metrics if m.get("write_time")]

        summary = {
            "count": len(metrics),
            "time_range_hours": hours,
            "total_time_stats": (
                {
                    "mean": float(np.mean(total_times)) if total_times else None,
                    "median": float(np.median(total_times)) if total_times else None,
                    "std": float(np.std(total_times)) if total_times else None,
                }
                if total_times
                else None
            ),
            "load_time_stats": (
                {
                    "mean": float(np.mean(load_times)) if load_times else None,
                    "median": float(np.median(load_times)) if load_times else None,
                }
                if load_times
                else None
            ),
            "write_time_stats": (
                {
                    "mean": float(np.mean(write_times)) if write_times else None,
                    "median": float(np.median(write_times)) if write_times else None,
                }
                if write_times
                else None
            ),
        }

        return {"metrics": metrics, "summary": summary}

    except Exception as e:
        logger.error(f"Failed to fetch performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/plots/stage-duration")
def get_stage_duration_plot(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return stage duration trends plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of stage duration trends
    """
    from dsa110_contimg.qa.performance_monitoring import (
        fetch_performance_metrics,
        plot_stage_duration_trends,
    )

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_performance_metrics(queue_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics found")

        output_path = plot_stage_duration_trends(metrics, output_dir / "stage_duration_trends.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="stage_duration_trends.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate stage duration plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/plots/writer-comparison")
def get_writer_comparison_plot(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return writer performance comparison plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of writer performance comparison
    """
    from dsa110_contimg.qa.performance_monitoring import (
        fetch_performance_metrics,
        plot_writer_performance_comparison,
    )

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_performance_metrics(queue_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics found")

        output_path = plot_writer_performance_comparison(
            metrics, output_dir / "writer_comparison.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="writer_comparison.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate writer comparison plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/plots/throughput")
def get_throughput_plot(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return pipeline throughput plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of pipeline throughput
    """
    from dsa110_contimg.qa.performance_monitoring import (
        fetch_performance_metrics,
        plot_pipeline_throughput,
    )

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_performance_metrics(queue_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics found")

        output_path = plot_pipeline_throughput(metrics, output_dir / "throughput.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="throughput.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate throughput plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/plots/failure-rate")
def get_failure_rate_plot(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return failure rate tracking plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of failure rate tracking
    """
    from dsa110_contimg.qa.performance_monitoring import plot_failure_rate_tracking

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        output_path = plot_failure_rate_tracking(
            queue_db, output_dir / "failure_rate.png", hours=hours
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=404, detail="No data available")

        return FileResponse(output_path, media_type="image/png", filename="failure_rate.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate failure rate plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Antenna Health Monitoring Endpoints
# ============================================================================


@router.get("/antenna-health/metrics")
def get_antenna_health_metrics(
    hours: int = Query(24, description="Hours of history to fetch")
) -> Dict[str, Any]:
    """Get raw antenna health metrics data.

    Returns aggregated antenna metrics from QA artifacts.

    Args:
        hours: Number of hours of history to fetch

    Returns:
        Dict with metrics list and summary statistics
    """
    from dsa110_contimg.qa.antenna_health_monitoring import fetch_antenna_qa_history

    _, products_db = _get_default_paths()

    try:
        metrics = fetch_antenna_qa_history(products_db, hours=hours)

        if not metrics:
            return {"metrics": [], "summary": {"count": 0, "error": "No antenna metrics found"}}

        # Extract unique antennas
        antennas = set()
        for m in metrics:
            if "rankings" in m:
                for entry in m["rankings"]:
                    antennas.add(entry["antenna"])

        summary = {
            "count": len(metrics),
            "unique_antennas": len(antennas),
            "time_range_hours": hours,
        }

        return {"metrics": metrics, "summary": summary}

    except Exception as e:
        logger.error(f"Failed to fetch antenna health metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/antenna-health/plots/heatmap")
def get_antenna_health_heatmap(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return antenna health heatmap.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of antenna health heatmap
    """
    from dsa110_contimg.qa.antenna_health_monitoring import (
        fetch_antenna_qa_history,
        plot_antenna_health_heatmap,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_antenna_qa_history(products_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No antenna metrics found")

        output_path = plot_antenna_health_heatmap(
            metrics, output_dir / "antenna_health_heatmap.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="antenna_health_heatmap.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate antenna health heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/antenna-health/plots/stability-trends")
def get_antenna_stability_trends(
    hours: int = Query(24, description="Hours of history to plot"),
    top_n: int = Query(10, description="Number of top antennas to plot"),
) -> FileResponse:
    """Generate and return antenna stability trends plot.

    Args:
        hours: Number of hours of history to plot
        top_n: Number of top antennas to plot

    Returns:
        PNG image of antenna stability trends
    """
    from dsa110_contimg.qa.antenna_health_monitoring import (
        fetch_antenna_qa_history,
        plot_per_antenna_stability_trends,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_antenna_qa_history(products_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No antenna metrics found")

        output_path = plot_per_antenna_stability_trends(
            metrics, output_dir / "antenna_stability_trends.png", top_n=top_n
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="antenna_stability_trends.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate antenna stability trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/antenna-health/plots/refant-report")
def get_refant_stability_report(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return reference antenna stability report.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of refant stability report
    """
    from dsa110_contimg.qa.antenna_health_monitoring import (
        fetch_antenna_qa_history,
        generate_refant_stability_report,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_antenna_qa_history(products_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No antenna metrics found")

        output_path = generate_refant_stability_report(
            metrics, output_dir / "refant_stability_report.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="refant_stability_report.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate refant stability report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Queue Health Monitoring Endpoints
# ============================================================================


@router.get("/queue-health/metrics")
def get_queue_health_metrics(
    hours: int = Query(24, description="Hours of history to fetch")
) -> Dict[str, Any]:
    """Get raw queue health metrics data.

    Returns queue state history including processing times and states.

    Args:
        hours: Number of hours of history to fetch

    Returns:
        Dict with metrics list and summary statistics
    """
    from dsa110_contimg.qa.queue_health_monitoring import fetch_queue_history

    queue_db, _ = _get_default_paths()

    try:
        history = fetch_queue_history(queue_db, hours=hours)

        if not history:
            return {"history": [], "summary": {"count": 0, "error": "No queue history found"}}

        # Calculate summary statistics
        from collections import Counter

        import numpy as np

        state_counts = Counter(g["state"] for g in history)

        # Processing times for completed groups
        completed = [g for g in history if g["state"] == "completed"]
        processing_times = []
        if completed:
            processing_times = [
                (g["last_update"] - g["received_at"]) / 60.0 for g in completed  # minutes
            ]

        summary = {
            "count": len(history),
            "time_range_hours": hours,
            "state_distribution": dict(state_counts),
            "processing_time_stats": (
                {
                    "mean": float(np.mean(processing_times)) if processing_times else None,
                    "median": float(np.median(processing_times)) if processing_times else None,
                    "p95": float(np.percentile(processing_times, 95)) if processing_times else None,
                    "p99": float(np.percentile(processing_times, 99)) if processing_times else None,
                }
                if processing_times
                else None
            ),
        }

        return {"history": history, "summary": summary}

    except Exception as e:
        logger.error(f"Failed to fetch queue health metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-health/plots/depth-trends")
def get_queue_depth_trends(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return queue depth trends plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of queue depth trends
    """
    from dsa110_contimg.qa.queue_health_monitoring import (
        fetch_queue_history,
        plot_queue_depth_trends,
    )

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        history = fetch_queue_history(queue_db, hours=hours)

        if not history:
            raise HTTPException(status_code=404, detail="No queue history found")

        output_path = plot_queue_depth_trends(history, output_dir / "queue_depth_trends.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="queue_depth_trends.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate queue depth trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-health/plots/processing-rate")
def get_processing_rate_plot(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return processing rate plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of processing rate
    """
    from dsa110_contimg.qa.queue_health_monitoring import fetch_queue_history, plot_processing_rate

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        history = fetch_queue_history(queue_db, hours=hours)

        if not history:
            raise HTTPException(status_code=404, detail="No queue history found")

        output_path = plot_processing_rate(history, output_dir / "processing_rate.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="processing_rate.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate processing rate plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-health/plots/time-to-completion")
def get_time_to_completion_cdf(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return time-to-completion CDF plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of time-to-completion CDF
    """
    from dsa110_contimg.qa.queue_health_monitoring import (
        fetch_queue_history,
        plot_time_to_completion_cdf,
    )

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        history = fetch_queue_history(queue_db, hours=hours)

        if not history:
            raise HTTPException(status_code=404, detail="No queue history found")

        output_path = plot_time_to_completion_cdf(
            history, output_dir / "time_to_completion_cdf.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="time_to_completion_cdf.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate time-to-completion CDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-health/plots/state-transitions")
def get_queue_state_transitions(
    hours: int = Query(24, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return queue state transitions plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of queue state transitions
    """
    from dsa110_contimg.qa.queue_health_monitoring import (
        fetch_queue_history,
        plot_queue_state_transitions,
    )

    queue_db, _ = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        history = fetch_queue_history(queue_db, hours=hours)

        if not history:
            raise HTTPException(status_code=404, detail="No queue history found")

        output_path = plot_queue_state_transitions(
            history, output_dir / "queue_state_transitions.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="queue_state_transitions.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate queue state transitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Combined Dashboard Endpoint
# ============================================================================


@router.get("/dashboard/summary")
def get_monitoring_dashboard_summary(
    hours: int = Query(24, description="Hours of history to include")
) -> Dict[str, Any]:
    """Get combined monitoring dashboard summary.

    Returns summary data for all monitoring categories:
    - Performance metrics
    - Antenna health
    - Queue health

    Args:
        hours: Number of hours of history to include

    Returns:
        Dict with summary data from all monitoring modules
    """
    from dsa110_contimg.qa.antenna_health_monitoring import fetch_antenna_qa_history
    from dsa110_contimg.qa.performance_monitoring import fetch_performance_metrics
    from dsa110_contimg.qa.queue_health_monitoring import fetch_queue_history

    queue_db, products_db = _get_default_paths()

    dashboard = {
        "timestamp": None,
        "time_range_hours": hours,
        "performance": {},
        "antenna_health": {},
        "queue_health": {},
    }

    import time
    from collections import Counter

    import numpy as np

    dashboard["timestamp"] = time.time()

    # Performance metrics
    try:
        perf_metrics = fetch_performance_metrics(queue_db, hours=hours)
        if perf_metrics:
            total_times = [m["total_time"] for m in perf_metrics if m.get("total_time")]
            dashboard["performance"] = {
                "count": len(perf_metrics),
                "mean_total_time_sec": float(np.mean(total_times)) if total_times else None,
                "median_total_time_sec": float(np.median(total_times)) if total_times else None,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch performance metrics: {e}")
        dashboard["performance"]["error"] = str(e)

    # Antenna health
    try:
        ant_metrics = fetch_antenna_qa_history(products_db, hours=hours)
        if ant_metrics:
            antennas = set()
            for m in ant_metrics:
                if "rankings" in m:
                    for entry in m["rankings"]:
                        antennas.add(entry["antenna"])

            dashboard["antenna_health"] = {
                "count": len(ant_metrics),
                "unique_antennas": len(antennas),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch antenna health metrics: {e}")
        dashboard["antenna_health"]["error"] = str(e)

    # Queue health
    try:
        queue_history = fetch_queue_history(queue_db, hours=hours)
        if queue_history:
            state_counts = Counter(g["state"] for g in queue_history)
            completed = [g for g in queue_history if g["state"] == "completed"]

            processing_times = []
            if completed:
                processing_times = [(g["last_update"] - g["received_at"]) / 60.0 for g in completed]

            dashboard["queue_health"] = {
                "total_groups": len(queue_history),
                "state_distribution": dict(state_counts),
                "completed_groups": len(completed),
                "median_processing_time_min": (
                    float(np.median(processing_times)) if processing_times else None
                ),
                "p95_processing_time_min": (
                    float(np.percentile(processing_times, 95)) if processing_times else None
                ),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch queue health metrics: {e}")
        dashboard["queue_health"]["error"] = str(e)

    return dashboard


# ============================================================================
# Mosaic Quality Monitoring Endpoints
# ============================================================================


@router.get("/mosaic-quality/metrics")
def get_mosaic_quality_metrics(
    hours: int = Query(168, description="Hours of history to fetch (default: 7 days)")
) -> Dict[str, Any]:
    """Get raw mosaic quality metrics data.

    Returns metrics from the mosaics table including RMS, dynamic range, source counts.

    Args:
        hours: Number of hours of history to fetch

    Returns:
        Dict with metrics list and summary statistics
    """
    from dsa110_contimg.qa.mosaic_quality_monitoring import fetch_mosaic_quality_metrics

    _, products_db = _get_default_paths()

    try:
        metrics = fetch_mosaic_quality_metrics(products_db, hours=hours)

        if not metrics:
            return {"metrics": [], "summary": {"count": 0, "error": "No mosaic metrics found"}}

        # Calculate summary statistics
        import numpy as np

        rms_values = [
            m.get("noise_jy") or m.get("rms_noise")
            for m in metrics
            if m.get("noise_jy") or m.get("rms_noise")
        ]
        dr_values = [m.get("dynamic_range") for m in metrics if m.get("dynamic_range")]
        source_counts = [m.get("source_count") for m in metrics if m.get("source_count")]

        summary = {
            "count": len(metrics),
            "time_range_hours": hours,
            "rms_stats": (
                {
                    "mean_jy": float(np.mean(rms_values)) if rms_values else None,
                    "median_jy": float(np.median(rms_values)) if rms_values else None,
                }
                if rms_values
                else None
            ),
            "dynamic_range_stats": (
                {
                    "mean": float(np.mean(dr_values)) if dr_values else None,
                    "median": float(np.median(dr_values)) if dr_values else None,
                }
                if dr_values
                else None
            ),
            "source_count_stats": (
                {
                    "mean": float(np.mean(source_counts)) if source_counts else None,
                    "median": float(np.median(source_counts)) if source_counts else None,
                }
                if source_counts
                else None
            ),
        }

        return {"metrics": metrics, "summary": summary}

    except Exception as e:
        logger.error(f"Failed to fetch mosaic quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mosaic-quality/plots/rms-trends")
def get_mosaic_rms_trends(
    hours: int = Query(168, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return mosaic RMS trends plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of mosaic RMS trends
    """
    from dsa110_contimg.qa.mosaic_quality_monitoring import (
        fetch_mosaic_quality_metrics,
        plot_mosaic_rms_trends,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_mosaic_quality_metrics(products_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No mosaic metrics found")

        output_path = plot_mosaic_rms_trends(metrics, output_dir / "mosaic_rms_trends.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="mosaic_rms_trends.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate mosaic RMS trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mosaic-quality/plots/dynamic-range")
def get_mosaic_dynamic_range(
    hours: int = Query(168, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return mosaic dynamic range trends plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of mosaic dynamic range trends
    """
    from dsa110_contimg.qa.mosaic_quality_monitoring import (
        fetch_mosaic_quality_metrics,
        plot_mosaic_dynamic_range_trends,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_mosaic_quality_metrics(products_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No mosaic metrics found")

        output_path = plot_mosaic_dynamic_range_trends(
            metrics, output_dir / "mosaic_dynamic_range.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="mosaic_dynamic_range.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate mosaic dynamic range plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Calibration Quality Monitoring Endpoints
# ============================================================================


@router.get("/calibration-quality/metrics")
def get_calibration_quality_metrics(
    hours: int = Query(168, description="Hours of history to fetch (default: 7 days)")
) -> Dict[str, Any]:
    """Get raw calibration quality metrics data.

    Returns metrics from calibration_qa table including SNR, convergence, flagging.

    Args:
        hours: Number of hours of history to fetch

    Returns:
        Dict with metrics list and summary statistics
    """
    from dsa110_contimg.qa.calibration_quality_monitoring import fetch_calibration_quality_metrics

    _, products_db = _get_default_paths()

    try:
        metrics = fetch_calibration_quality_metrics(products_db, hours=hours)

        if not metrics:
            return {"metrics": [], "summary": {"count": 0, "error": "No calibration metrics found"}}

        # Calculate summary statistics
        from collections import Counter

        quality_dist = Counter(
            m.get("overall_quality") for m in metrics if m.get("overall_quality")
        )

        summary = {
            "count": len(metrics),
            "time_range_hours": hours,
            "quality_distribution": dict(quality_dist),
        }

        return {"metrics": metrics, "summary": summary}

    except Exception as e:
        logger.error(f"Failed to fetch calibration quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calibration-quality/plots/snr-trends")
def get_calibration_snr_trends(
    hours: int = Query(168, description="Hours of history to plot")
) -> FileResponse:
    """Generate and return calibration SNR trends plot.

    Args:
        hours: Number of hours of history to plot

    Returns:
        PNG image of calibration SNR trends
    """
    from dsa110_contimg.qa.calibration_quality_monitoring import (
        fetch_calibration_quality_metrics,
        plot_calibration_snr_trends,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        metrics = fetch_calibration_quality_metrics(products_db, hours=hours)

        if not metrics:
            raise HTTPException(status_code=404, detail="No calibration metrics found")

        output_path = plot_calibration_snr_trends(
            metrics, output_dir / "calibration_snr_trends.png"
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="calibration_snr_trends.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate calibration SNR trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Disk Usage Monitoring Endpoints
# ============================================================================


@router.get("/disk-usage/current")
def get_disk_usage_current() -> Dict[str, Any]:
    """Get current disk usage for monitored paths.

    Returns:
        Dict with current disk usage data
    """
    from dsa110_contimg.qa.disk_usage_monitoring import collect_current_disk_usage

    try:
        usage_data = collect_current_disk_usage()

        return {"timestamp": time.time(), "usage": usage_data}

    except Exception as e:
        logger.error(f"Failed to collect disk usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disk-usage/plots/current")
def get_disk_usage_plot() -> FileResponse:
    """Generate and return current disk usage plot.

    Returns:
        PNG image of current disk usage
    """
    from dsa110_contimg.qa.disk_usage_monitoring import (
        collect_current_disk_usage,
        plot_disk_usage_current,
    )

    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        usage_data = collect_current_disk_usage()

        if not usage_data:
            raise HTTPException(status_code=404, detail="No disk usage data available")

        output_path = plot_disk_usage_current(usage_data, output_dir / "disk_usage_current.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="disk_usage_current.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate disk usage plot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disk-usage/plots/projection")
def get_disk_usage_projection(
    days: int = Query(30, description="Days ahead to project")
) -> FileResponse:
    """Generate and return disk usage projection plot.

    Args:
        days: Number of days ahead to project

    Returns:
        PNG image of disk usage projection
    """
    from dsa110_contimg.qa.disk_usage_monitoring import (
        collect_current_disk_usage,
        plot_disk_usage_projection,
    )

    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        usage_data = collect_current_disk_usage()

        if not usage_data:
            raise HTTPException(status_code=404, detail="No disk usage data available")

        output_path = plot_disk_usage_projection(
            usage_data, output_dir / "disk_usage_projection.png", days_ahead=days
        )

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="disk_usage_projection.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate disk usage projection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ESE Candidate Dashboard Endpoints
# ============================================================================


@router.get("/ese-candidates/list")
def get_ese_candidates_list(
    status: Optional[str] = Query(
        "active", description="Filter by status (active, investigated, dismissed, or null for all)"
    ),
    min_sigma: float = Query(3.0, description="Minimum significance threshold"),
) -> Dict[str, Any]:
    """Get list of ESE candidates.

    Args:
        status: Filter by status
        min_sigma: Minimum significance threshold

    Returns:
        Dict with ESE candidates list
    """
    from dsa110_contimg.qa.ese_candidate_dashboard import fetch_ese_candidates

    _, products_db = _get_default_paths()

    try:
        candidates = fetch_ese_candidates(
            products_db, status=status if status != "null" else None, min_sigma=min_sigma
        )

        return {
            "candidates": candidates,
            "count": len(candidates),
            "filters": {"status": status, "min_sigma": min_sigma},
        }

    except Exception as e:
        logger.error(f"Failed to fetch ESE candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ese-candidates/plots/sky-distribution")
def get_ese_sky_distribution(
    min_sigma: float = Query(3.0, description="Minimum significance threshold")
) -> FileResponse:
    """Generate and return ESE candidate sky distribution plot.

    Args:
        min_sigma: Minimum significance threshold

    Returns:
        PNG image of ESE candidate sky distribution
    """
    from dsa110_contimg.qa.ese_candidate_dashboard import (
        fetch_ese_candidates,
        plot_ese_sky_distribution,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        candidates = fetch_ese_candidates(products_db, status="active", min_sigma=min_sigma)

        if not candidates:
            raise HTTPException(status_code=404, detail="No ESE candidates found")

        output_path = plot_ese_sky_distribution(candidates, output_dir / "ese_sky_distribution.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(
            output_path, media_type="image/png", filename="ese_sky_distribution.png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate ESE sky distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ese-candidates/plots/flux-variations")
def get_ese_flux_variations(
    min_sigma: float = Query(3.0, description="Minimum significance threshold")
) -> FileResponse:
    """Generate and return ESE flux variation plot.

    Args:
        min_sigma: Minimum significance threshold

    Returns:
        PNG image of ESE flux variations
    """
    from dsa110_contimg.qa.ese_candidate_dashboard import (
        fetch_ese_candidates,
        plot_ese_flux_variations,
    )

    _, products_db = _get_default_paths()
    output_dir = Path("/tmp/dsa110_monitoring_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        candidates = fetch_ese_candidates(products_db, status="active", min_sigma=min_sigma)

        if not candidates:
            raise HTTPException(status_code=404, detail="No ESE candidates found")

        output_path = plot_ese_flux_variations(candidates, output_dir / "ese_flux_variations.png")

        if not output_path or not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate plot")

        return FileResponse(output_path, media_type="image/png", filename="ese_flux_variations.png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate ESE flux variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
