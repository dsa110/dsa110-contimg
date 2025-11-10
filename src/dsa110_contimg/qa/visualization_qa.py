"""
Enhanced QA functions with visualization support.

Provides wrapper functions that integrate visualization framework
with existing QA functions.
"""

from typing import Optional, List, Dict, Any

try:
    from dsa110_contimg.qa.casa_ms_qa import (
        run_ms_qa,
        QaResult,
        QaThresholds,
    )
    HAS_QA = True
except ImportError:
    HAS_QA = False
    run_ms_qa = None  # type: ignore
    QaResult = None  # type: ignore
    QaThresholds = None  # type: ignore

from dsa110_contimg.qa.visualization.integration import (
    enhance_qa_with_notebook,
    display_qa_summary,
)


def run_ms_qa_with_visualization(
    ms_path: str,
    qa_root: str,
    thresholds: Optional[QaThresholds] = None,
    gaintables: Optional[List[str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
    generate_notebook: bool = True,
    display_summary: bool = False,
) -> QaResult:
    """
    Run MS QA with automatic visualization notebook generation.

    This is a wrapper around run_ms_qa() that automatically generates
    an interactive notebook for exploring QA results.

    Args:
        ms_path: Path to Measurement Set
        qa_root: Path to QA output directory
        thresholds: Optional QA thresholds
        gaintables: Optional calibration tables to test
        extra_metadata: Optional extra metadata
        generate_notebook: Whether to generate interactive notebook
        display_summary: Whether to display summary in Jupyter

    Returns:
        QaResult with notebook in artifacts (if generate_notebook=True)

    Example:
        >>> result = run_ms_qa_with_visualization(
        ...     "data.ms",
        ...     "state/qa",
        ...     generate_notebook=True
        ... )
        >>> # Notebook is in result.artifacts
    """
    if not HAS_QA:
        raise ImportError(
            "dsa110_contimg.qa.casa_ms_qa is required for QA functions"
        )

    # Run standard QA
    result = run_ms_qa(
        ms_path=ms_path,
        qa_root=qa_root,
        thresholds=thresholds,
        gaintables=gaintables,
        extra_metadata=extra_metadata,
    )

    # Enhance with visualization
    if generate_notebook:
        result = enhance_qa_with_notebook(result, auto_generate=True)

    # Display summary if requested
    if display_summary:
        display_qa_summary(result)

    return result
