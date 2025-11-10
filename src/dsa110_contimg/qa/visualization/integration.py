"""
Integration of visualization framework with QA functions.

Provides functions to enhance QA outputs with interactive visualization
and notebook generation.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from dsa110_contimg.qa.casa_ms_qa import QaResult
    HAS_QA = True
except ImportError:
    HAS_QA = False
    QaResult = None  # type: ignore

from .notebook import generate_qa_notebook
from .datadir import ls
from .render import render_status_message, display_html

try:
    from IPython.display import display, HTML
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    def display(*args, **kwargs):
        pass
    HTML = str


def generate_qa_notebook_from_result(
    result: QaResult,
    output_path: Optional[str] = None,
    include_ms: bool = True,
) -> str:
    """
    Generate a QA notebook from a QaResult object.

    Args:
        result: QaResult from run_ms_qa()
        output_path: Optional path to save notebook
        include_ms: Whether to include MS browsing in notebook

    Returns:
        Path to generated notebook file

    Example:
        >>> from dsa110_contimg.qa.casa_ms_qa import run_ms_qa
        >>> result = run_ms_qa("data.ms", "state/qa")
        >>> notebook = generate_qa_notebook_from_result(result)
    """
    if not HAS_QA:
        raise ImportError(
            "dsa110_contimg.qa.casa_ms_qa is required for QA integration"
        )

    ms_path = result.ms_path if include_ms else None
    qa_root = str(Path(result.artifacts[0]).parent) if result.artifacts else None

    # Filter artifacts to include only relevant ones
    artifacts = []
    for artifact in result.artifacts:
        artifact_path = Path(artifact)
        # Include FITS files, images, and other visualizable files
        if artifact_path.suffix.lower() in [
            ".fits", ".png", ".jpg", ".jpeg", ".gif", ".pdf"
        ]:
            artifacts.append(artifact)
        # Include MS files
        elif artifact_path.suffix.lower() == ".ms" or artifact_path.is_dir():
            artifacts.append(artifact)

    title = f"QA Report - {Path(result.ms_path).name}"
    if not result.success:
        title += " [FAILED]"

    return generate_qa_notebook(
        ms_path=ms_path,
        qa_root=qa_root,
        artifacts=artifacts,
        output_path=output_path,
        title=title,
    )


def browse_qa_outputs(qa_root: str) -> None:
    """
    Browse QA output directory interactively.

    Args:
        qa_root: Path to QA output directory

    Example:
        >>> browse_qa_outputs("state/qa/my_ms")
    """
    qa_dir = ls(qa_root)
    qa_dir.show()

    # Show FITS files if any
    fits_files = qa_dir.fits
    if fits_files:
        print(f"\nFound {len(fits_files)} FITS files:")
        fits_files.show()

    # Show images if any
    images = qa_dir.images
    if images:
        print(f"\nFound {len(images)} image files:")
        images.show()

    # Show MS files if any
    tables = qa_dir.tables
    if tables:
        print(f"\nFound {len(tables)} CASA tables:")
        tables.show()


def display_qa_summary(result: QaResult) -> None:
    """
    Display a formatted QA result summary.

    Args:
        result: QaResult from run_ms_qa()

    Example:
        >>> result = run_ms_qa("data.ms", "state/qa")
        >>> display_qa_summary(result)
    """
    if not HAS_QA:
        raise ImportError(
            "dsa110_contimg.qa.casa_ms_qa is required for QA integration"
        )

    if not HAS_IPYTHON:
        # Fallback to print
        print(f"QA Result: {'PASS' if result.success else 'FAIL'}")
        print(f"MS Path: {result.ms_path}")
        if result.reasons:
            print("Reasons:")
            for reason in result.reasons:
                print(f"  - {reason}")
        print(f"Artifacts: {len(result.artifacts)}")
        return

    from .render import render_table

    # Status message
    status_type = "success" if result.success else "error"
    status_msg = f"QA Result: {'PASS' if result.success else 'FAIL'}"
    html = render_status_message(status_msg, message_type=status_type)

    # Summary table
    data = [
        ("MS Path", result.ms_path),
        ("Success", "Yes" if result.success else "No"),
        ("Artifacts", str(len(result.artifacts))),
    ]

    if result.reasons:
        reasons_str = "; ".join(result.reasons[:3])
        if len(result.reasons) > 3:
            reasons_str += f" ... ({len(result.reasons) - 3} more)"
        data.append(("Reasons", reasons_str))

    html += render_table(data, headers=["Property", "Value"], numbering=False)

    # Artifacts list
    if result.artifacts:
        html += "<h4>Artifacts</h4>"
        artifacts_data = [
            (i + 1, Path(artifact).name) for i, artifact in enumerate(result.artifacts)
        ]
        html += render_table(
            artifacts_data,
            headers=["#", "Artifact"],
            numbering=False,
        )

    display(HTML(html))


def enhance_qa_with_notebook(
    result: QaResult,
    auto_generate: bool = True,
    notebook_path: Optional[str] = None,
) -> QaResult:
    """
    Enhance a QA result by generating an interactive notebook.

    Args:
        result: QaResult from run_ms_qa()
        auto_generate: Whether to automatically generate notebook
        notebook_path: Optional path for notebook (auto-generated if None)

    Returns:
        Enhanced QaResult with notebook in artifacts

    Example:
        >>> result = run_ms_qa("data.ms", "state/qa")
        >>> enhanced = enhance_qa_with_notebook(result)
        >>> # Notebook is now in enhanced.artifacts
    """
    if not HAS_QA:
        raise ImportError(
            "dsa110_contimg.qa.casa_ms_qa is required for QA integration"
        )

    if auto_generate:
        try:
            notebook_path = generate_qa_notebook_from_result(
                result,
                output_path=notebook_path,
            )
            # Add notebook to artifacts
            result.artifacts.append(notebook_path)
        except Exception as e:
            # Don't fail QA if notebook generation fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to generate QA notebook: {e}")

    return result


def create_qa_explorer_notebook(
    qa_root: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Create an explorer notebook for a QA output directory.

    Args:
        qa_root: Path to QA output directory
        output_path: Optional path to save notebook

    Returns:
        Path to generated notebook file

    Example:
        >>> notebook = create_qa_explorer_notebook("state/qa")
    """
    from .notebook import generate_qa_notebook

    # Find MS files and artifacts in QA directory
    qa_dir = ls(qa_root, recursive=True)
    ms_files = qa_dir.tables
    fits_files = qa_dir.fits
    images = qa_dir.images

    # Use first MS if available
    ms_path = str(ms_files[0].fullpath) if ms_files else None

    # Collect artifacts
    artifacts = []
    for fits_file in fits_files[:10]:  # Limit to first 10 FITS files
        artifacts.append(str(fits_file.fullpath))
    for img_file in images[:10]:  # Limit to first 10 images
        artifacts.append(str(img_file.fullpath))

    title = f"QA Explorer - {Path(qa_root).name}"

    return generate_qa_notebook(
        ms_path=ms_path,
        qa_root=qa_root,
        artifacts=artifacts,
        output_path=output_path,
        title=title,
    )

