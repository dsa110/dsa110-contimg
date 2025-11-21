"""
Notebook generation utilities for QA visualization framework.

Provides functions to programmatically generate Jupyter notebooks for QA
reports and interactive data exploration.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import nbformat

    HAS_NBFORMAT = True
except ImportError:
    HAS_NBFORMAT = False
    nbformat = None  # type: ignore


def generate_qa_notebook(
    ms_path: Optional[str] = None,
    qa_root: Optional[str] = None,
    artifacts: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """
    Generate a QA notebook for a Measurement Set and its artifacts.

    Args:
        ms_path: Path to Measurement Set (optional)
        qa_root: Path to QA output directory (optional)
        artifacts: List of artifact paths (FITS files, plots, etc.)
        output_path: Path to save notebook (.ipynb file)
        title: Optional notebook title

    Returns:
        Path to generated notebook file

    Example:
        >>> notebook_path = generate_qa_notebook(
        ...     ms_path="data.ms",
        ...     qa_root="state/qa",
        ...     artifacts=["image.fits", "plot.png"],
        ...     output_path="qa_report.ipynb"
        ... )
    """
    if not HAS_NBFORMAT:
        raise ImportError("nbformat is required for notebook generation")

    # Create notebook
    nb = nbformat.v4.new_notebook()

    # Add title cell
    if title is None:
        title = "QA Report"
        if ms_path:
            title += f" - {Path(ms_path).name}"
        if qa_root:
            title += f" ({Path(qa_root).name})"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Use Title() from layouts for better formatting
    title_code = f"""
# Display notebook title
from dsa110_contimg.qa.visualization import Title
Title("{title}", sections=["MS", "QA Directory", "Artifacts"])
print(f"Generated: {timestamp}")
"""
    nb.cells.append(nbformat.v4.new_code_cell(title_code))

    # Add imports cell
    imports_code = """
# QA Visualization Framework
from dsa110_contimg.qa.visualization import (
    FITSFile,
    ImageFile,
    TextFile,
    CasaTable,
    Title,
    Section,
    ls,
    init_js9,
    render_table,
    render_status_message,
)

# Initialize JS9 for FITS viewing
init_js9()

# Standard imports
import os
from pathlib import Path
"""
    nb.cells.append(nbformat.v4.new_code_cell(imports_code))

    # Add MS browsing cell if MS path provided
    if ms_path:
        ms_code = f"""
# Browse Measurement Set
Section("MS", refreshable=False)
ms = CasaTable("{ms_path}")
ms.show()

# Display table summary
print(f"Rows: {{ms.nrows:,}}")
print(f"Columns: {{len(ms.columns)}}")
# First 10 columns
print(f"\\nColumn names: {{ms.columns[:10]}}...")
"""
        nb.cells.append(nbformat.v4.new_code_cell(ms_code))

    # Add QA directory browsing cell if qa_root provided
    if qa_root:
        qa_code = f"""
# Browse QA output directory
Section("QA Directory", refreshable=False)
qa_dir = ls("{qa_root}")
qa_dir.show()

# Find FITS files
fits_files = qa_dir.fits
if fits_files:
    print(f"Found {{len(fits_files)}} FITS files")
    fits_files.show()

# Find image files
images = qa_dir.images
if images:
    print(f"\\nFound {{len(images)}} image files")
    images.show()

# Find text/log files
text_files = [
    f for f in qa_dir
    if hasattr(f, 'fullpath') and
    str(f.fullpath).endswith(('.log', '.txt', '.out', '.err'))
]
if text_files:
    print(f"\\nFound {{len(text_files)}} text/log files")
"""
        nb.cells.append(nbformat.v4.new_code_cell(qa_code))

    # Add artifact viewing cells
    if artifacts:
        artifacts_code = """
Section("Artifacts", refreshable=False)
"""
        nb.cells.append(nbformat.v4.new_code_cell(artifacts_code))

        for artifact in artifacts:
            artifact_path = Path(artifact)
            if artifact_path.suffix.lower() == ".fits":
                # FITS file - use enhanced features
                fits_code = f"""
# View FITS file: {artifact_path.name}
fits = FITSFile("{artifact}")
# Use enhanced features: dual-window for comparison, configurable scale/colormap
fits.show(dual_window=False, scale="linear", colormap="grey")
"""
                nb.cells.append(nbformat.v4.new_code_cell(fits_code))
            elif artifact_path.suffix.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
            ]:
                # Image file - use ImageFile class
                img_code = f"""
# Display image: {artifact_path.name}
img = ImageFile("{artifact}")
img.show()
# Or show as thumbnail
# img.render_thumb(width=300)
"""
                nb.cells.append(nbformat.v4.new_code_cell(img_code))
            elif artifact_path.suffix.lower() in [
                ".txt",
                ".log",
                ".out",
                ".err",
                ".dat",
            ]:
                # Text file - use TextFile class
                text_code = f"""
# View text file: {artifact_path.name}
text = TextFile("{artifact}")
# Show first 50 lines
text.head(50).show()
# Or use grep to search
# text.grep("ERROR").show()
"""
                nb.cells.append(nbformat.v4.new_code_cell(text_code))
            elif artifact_path.suffix.lower() == ".ms" or artifact_path.is_dir():
                # CASA table
                table_code = f"""
# Browse CASA table: {artifact_path.name}
table = CasaTable("{artifact}")
table.show()
"""
                nb.cells.append(nbformat.v4.new_code_cell(table_code))

    # Add footer cell
    footer_code = """
# Notebook complete
msg = "QA notebook generated successfully"
render_status_message(msg, message_type="success")
"""
    nb.cells.append(nbformat.v4.new_code_cell(footer_code))

    # Save notebook
    if output_path is None:
        if ms_path:
            base_name = Path(ms_path).stem
        elif qa_root:
            base_name = Path(qa_root).name
        else:
            base_name = "qa_report"
        output_path = f"{base_name}_qa.ipynb"

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path_obj, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    return str(output_path_obj.resolve())


def generate_fits_viewer_notebook(
    fits_paths: List[str],
    output_path: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """
    Generate a notebook for viewing multiple FITS files.

    Args:
        fits_paths: List of FITS file paths
        output_path: Path to save notebook
        title: Optional notebook title

    Returns:
        Path to generated notebook file
    """
    if not HAS_NBFORMAT:
        raise ImportError("nbformat is required for notebook generation")

    nb = nbformat.v4.new_notebook()

    if title is None:
        title = f"FITS Viewer - {len(fits_paths)} files"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nb.cells.append(nbformat.v4.new_markdown_cell(f"# {title}\n\nGenerated: {timestamp}"))

    # Imports
    imports_code = """
from dsa110_contimg.qa.visualization import FITSFile, init_js9, ls

# Initialize JS9
init_js9()
"""
    nb.cells.append(nbformat.v4.new_code_cell(imports_code))

    # Add cells for each FITS file
    for i, fits_path in enumerate(fits_paths, 1):
        fits_name = Path(fits_path).name
        nb.cells.append(nbformat.v4.new_markdown_cell(f"## FITS File {i}: {fits_name}"))

        fits_code = f"""
fits_{i} = FITSFile("{fits_path}")
fits_{i}.show()
"""
        nb.cells.append(nbformat.v4.new_code_cell(fits_code))

    # Save notebook
    if output_path is None:
        output_path = f"fits_viewer_{len(fits_paths)}_files.ipynb"

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path_obj, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    return str(output_path_obj.resolve())


def generate_ms_explorer_notebook(
    ms_path: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """
    Generate a notebook for exploring a Measurement Set.

    Args:
        ms_path: Path to Measurement Set
        output_path: Path to save notebook
        title: Optional notebook title

    Returns:
        Path to generated notebook file
    """
    if not HAS_NBFORMAT:
        raise ImportError("nbformat is required for notebook generation")

    nb = nbformat.v4.new_notebook()

    if title is None:
        title = f"MS Explorer - {Path(ms_path).name}"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nb.cells.append(nbformat.v4.new_markdown_cell(f"# {title}\n\nGenerated: {timestamp}"))

    # Imports
    imports_code = """
from dsa110_contimg.qa.visualization import CasaTable, render_table
import numpy as np
"""
    nb.cells.append(nbformat.v4.new_code_cell(imports_code))

    # Open MS
    open_ms_code = f"""
# Open Measurement Set
ms = CasaTable("{ms_path}")
ms.show()
"""
    nb.cells.append(nbformat.v4.new_code_cell(open_ms_code))

    # Table summary
    summary_code = """
# Table Summary
print(f"Rows: {ms.nrows:,}")
print(f"Columns: {len(ms.columns)}")
print(f"\\nColumns: {ms.columns}")
"""
    nb.cells.append(nbformat.v4.new_code_cell(summary_code))

    # Sample data
    sample_code = """
# Sample Data (first 10 rows)
if ms.nrows > 0:
    # Get first few columns
    sample_cols = ms.columns[:5]
    for col in sample_cols:
        try:
            data = ms.getcol(col, start=0, nrow=10)
            print(f"\\n{col}:")
            shape_str = (
                data.shape if hasattr(data, 'shape') else 'scalar'
            )
            print(f"  Shape: {shape_str}")
            sample = data[:3] if hasattr(data, '__getitem__') else data
            print(f"  Sample: {sample}")
        except Exception as e:
            print(f"\\n{col}: Error - {e}")
"""
    nb.cells.append(nbformat.v4.new_code_cell(sample_code))

    # Subtables
    subtables_code = """
# Browse Subtables
if ms.subtables:
    print("Available subtables:")
    for subtable in ms.subtables:
        print(f"  - {subtable}")

    # Open first subtable if available
    if ms.subtables:
        from os.path import basename
        subtable_name = basename(ms.subtables[0])
        try:
            subtable = ms[subtable_name]
            subtable.show()
        except Exception as e:
            print(f"Error opening subtable: {e}")
"""
    nb.cells.append(nbformat.v4.new_code_cell(subtables_code))

    # Save notebook
    if output_path is None:
        base_name = Path(ms_path).stem
        output_path = f"{base_name}_explorer.ipynb"

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path_obj, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    return str(output_path_obj.resolve())


def add_cell_to_notebook(
    notebook_path: str,
    cell_type: str = "code",
    content: str = "",
    position: Optional[int] = None,
) -> None:
    """
    Add a cell to an existing notebook.

    Args:
        notebook_path: Path to notebook file
        cell_type: Cell type ("code" or "markdown")
        content: Cell content
        position: Position to insert (None for append)
    """
    if not HAS_NBFORMAT:
        raise ImportError("nbformat is required for notebook generation")

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    if cell_type == "code":
        new_cell = nbformat.v4.new_code_cell(content)
    elif cell_type == "markdown":
        new_cell = nbformat.v4.new_markdown_cell(content)
    else:
        raise ValueError(f"Invalid cell_type: {cell_type}")

    if position is None:
        nb.cells.append(new_cell)
    else:
        nb.cells.insert(position, new_cell)

    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
