"""
Report generation utilities for producing HTML/PDF reports.

Provides:
- HTML report generation with embedded figures
- Multi-page PDF reports
- Diagnostic summary pages

Adapted from ASKAP-continuum-validation/report.py patterns.
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Sequence, Union

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """A section within a report."""

    title: str
    content: str = ""
    figures: list["Figure"] = field(default_factory=list)
    figure_captions: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    table_captions: list[str] = field(default_factory=list)
    level: int = 2  # Heading level (2 = h2)


@dataclass
class ReportMetadata:
    """Metadata for a report."""

    title: str = "DSA-110 Pipeline Report"
    author: str = "DSA-110 Continuum Imaging Pipeline"
    date: datetime = field(default_factory=datetime.now)
    observation_id: Optional[str] = None
    pipeline_version: Optional[str] = None

    def __post_init__(self):
        if self.pipeline_version is None:
            try:
                from dsa110_contimg import __version__

                self.pipeline_version = __version__
            except ImportError:
                self.pipeline_version = "unknown"


def _figure_to_base64(fig: "Figure", format: str = "png", dpi: int = 100) -> str:
    """Convert matplotlib figure to base64 string for embedding."""
    buf = io.BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _table_to_html(data: dict[str, Any], caption: str = "") -> str:
    """Convert dictionary data to HTML table."""
    lines = ["<table class='data-table'>"]
    if caption:
        lines.append(f"<caption>{caption}</caption>")
    lines.append("<thead><tr><th>Parameter</th><th>Value</th></tr></thead>")
    lines.append("<tbody>")

    for key, value in data.items():
        if isinstance(value, float):
            value_str = f"{value:.4g}"
        elif isinstance(value, (list, tuple)):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        lines.append(f"<tr><td>{key}</td><td>{value_str}</td></tr>")

    lines.append("</tbody></table>")
    return "\n".join(lines)


# HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        header {{
            border-bottom: 2px solid #333;
            margin-bottom: 30px;
            padding-bottom: 10px;
        }}
        h1 {{ color: #2c3e50; }}
        h2 {{
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
        }}
        h3 {{ color: #7f8c8d; }}
        .meta {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .figure {{
            text-align: center;
            margin: 20px 0;
        }}
        .figure img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .figure-caption {{
            font-style: italic;
            color: #666;
            margin-top: 10px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .data-table th, .data-table td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        .data-table th {{
            background-color: #f5f5f5;
        }}
        .data-table caption {{
            caption-side: top;
            font-weight: bold;
            padding: 10px;
        }}
        .data-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .error {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .success {{
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #999;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <div class="meta">
            <p>Generated: {date} | Author: {author}</p>
            {observation_line}
            {version_line}
        </div>
    </header>

    {content}

    <footer>
        <p>Generated by DSA-110 Continuum Imaging Pipeline v{version}</p>
    </footer>
</body>
</html>
"""


def generate_html_report(
    sections: Sequence[ReportSection],
    output: Union[str, Path],
    metadata: Optional[ReportMetadata] = None,
) -> Path:
    """Generate an HTML report with embedded figures.

    Args:
        sections: Report sections to include
        output: Output file path
        metadata: Report metadata

    Returns:
        Path to generated report
    """
    if metadata is None:
        metadata = ReportMetadata()

    output = Path(output)

    # Build content from sections
    content_parts = []

    for section in sections:
        heading_tag = f"h{section.level}"
        content_parts.append(f"<{heading_tag}>{section.title}</{heading_tag}>")

        if section.content:
            content_parts.append(f"<p>{section.content}</p>")

        # Embed figures
        for idx, fig in enumerate(section.figures):
            b64_img = _figure_to_base64(fig)
            caption = section.figure_captions[idx] if idx < len(section.figure_captions) else ""
            content_parts.append(
                f'<div class="figure">'
                f'<img src="data:image/png;base64,{b64_img}" alt="{caption}">'
                f'<div class="figure-caption">{caption}</div>'
                f"</div>"
            )

        # Add tables
        for idx, table in enumerate(section.tables):
            caption = section.table_captions[idx] if idx < len(section.table_captions) else ""
            content_parts.append(_table_to_html(table, caption))

    content = "\n".join(content_parts)

    # Build metadata lines
    obs_line = f"<p>Observation: {metadata.observation_id}</p>" if metadata.observation_id else ""
    ver_line = (
        f"<p>Pipeline Version: {metadata.pipeline_version}</p>" if metadata.pipeline_version else ""
    )

    html = HTML_TEMPLATE.format(
        title=metadata.title,
        date=metadata.date.strftime("%Y-%m-%d %H:%M:%S"),
        author=metadata.author,
        observation_line=obs_line,
        version_line=ver_line,
        version=metadata.pipeline_version or "unknown",
        content=content,
    )

    output.write_text(html)
    logger.info(f"Generated HTML report: {output}")

    return output


def generate_pdf_report(
    sections: Sequence[ReportSection],
    output: Union[str, Path],
    metadata: Optional[ReportMetadata] = None,
) -> Path:
    """Generate a PDF report using matplotlib's PdfPages.

    Args:
        sections: Report sections to include
        output: Output file path
        metadata: Report metadata

    Returns:
        Path to generated report
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    if metadata is None:
        metadata = ReportMetadata()

    output = Path(output)

    with PdfPages(output) as pdf:
        # Title page
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.7, metadata.title, ha="center", va="center", fontsize=24, fontweight="bold")
        fig.text(
            0.5,
            0.55,
            f"Generated: {metadata.date.strftime('%Y-%m-%d %H:%M:%S')}",
            ha="center",
            va="center",
            fontsize=12,
        )
        fig.text(0.5, 0.5, f"Author: {metadata.author}", ha="center", va="center", fontsize=12)
        if metadata.observation_id:
            fig.text(
                0.5,
                0.45,
                f"Observation: {metadata.observation_id}",
                ha="center",
                va="center",
                fontsize=12,
            )
        fig.text(
            0.5,
            0.35,
            f"Pipeline Version: {metadata.pipeline_version}",
            ha="center",
            va="center",
            fontsize=10,
            color="gray",
        )
        pdf.savefig(fig)
        plt.close(fig)

        # Section pages
        for section in sections:
            # Section header page if there's text content
            if section.content:
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(
                    0.5, 0.9, section.title, ha="center", va="top", fontsize=18, fontweight="bold"
                )

                # Wrap text content
                wrapped_text = "\n".join(
                    section.content[i : i + 80] for i in range(0, len(section.content), 80)
                )
                fig.text(0.1, 0.8, wrapped_text, ha="left", va="top", fontsize=10, wrap=True)
                pdf.savefig(fig)
                plt.close(fig)

            # Add figures
            for idx, figure in enumerate(section.figures):
                # Clone the figure to add caption
                pdf.savefig(figure)

        # Set PDF metadata
        d = pdf.infodict()
        d["Title"] = metadata.title
        d["Author"] = metadata.author
        d["CreationDate"] = metadata.date

    logger.info(f"Generated PDF report: {output}")

    return output


def create_diagnostic_report(
    ms_path: Union[str, Path],
    output_dir: Union[str, Path],
    include_calibration: bool = True,
    include_imaging: bool = True,
) -> Path:
    """Create a comprehensive diagnostic report for an observation.

    This is a convenience function that generates all relevant plots
    and assembles them into an HTML report.

    Args:
        ms_path: Path to measurement set
        output_dir: Directory for output files
        include_calibration: Include calibration diagnostic plots
        include_imaging: Include imaging diagnostic plots

    Returns:
        Path to generated report
    """
    from dsa110_contimg.visualization import (
        FigureConfig,
        PlotStyle,
    )

    ms_path = Path(ms_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = FigureConfig(style=PlotStyle.QUICKLOOK)
    sections = []

    # Overview section
    overview = ReportSection(
        title="Observation Overview",
        content=f"Diagnostic report for {ms_path.name}",
        tables=[
            {
                "Measurement Set": ms_path.name,
                "Path": str(ms_path),
                "Report Generated": datetime.now().isoformat(),
            }
        ],
        table_captions=["Observation Information"],
    )
    sections.append(overview)

    # Calibration section
    if include_calibration:
        cal_section = ReportSection(
            title="Calibration Diagnostics",
            content="Calibration solution quality metrics.",
        )

        # Try to find and plot calibration tables
        caltable_dir = ms_path.parent
        for pattern in ["*.bcal", "*.gcal", "*.kcal", "*.B", "*.G", "*.K"]:
            for caltable in caltable_dir.glob(pattern):
                try:
                    # Import here to avoid circular imports
                    from dsa110_contimg.visualization.calibration_plots import (
                        plot_bandpass,
                        plot_delays,
                        plot_gains,
                    )

                    if "bcal" in caltable.name.lower() or caltable.suffix == ".B":
                        fig = plot_bandpass(caltable, config=config)
                        cal_section.figures.append(fig)
                        cal_section.figure_captions.append(f"Bandpass: {caltable.name}")
                    elif "gcal" in caltable.name.lower() or caltable.suffix == ".G":
                        fig = plot_gains(caltable, config=config)
                        cal_section.figures.append(fig)
                        cal_section.figure_captions.append(f"Gains: {caltable.name}")
                    elif "kcal" in caltable.name.lower() or caltable.suffix == ".K":
                        fig = plot_delays(caltable, config=config)
                        cal_section.figures.append(fig)
                        cal_section.figure_captions.append(f"Delays: {caltable.name}")
                except Exception as e:
                    logger.warning(f"Failed to plot {caltable}: {e}")

        if cal_section.figures:
            sections.append(cal_section)

    # Imaging section placeholder
    if include_imaging:
        img_section = ReportSection(
            title="Imaging Diagnostics",
            content="Image quality metrics and diagnostics.",
        )

        # Look for image products
        image_dir = output_dir / "images"
        if image_dir.exists():
            for fits_file in image_dir.glob("*.fits"):
                try:
                    from dsa110_contimg.visualization.fits_plots import plot_fits_image

                    fig = plot_fits_image(fits_file, config=config)
                    img_section.figures.append(fig)
                    img_section.figure_captions.append(f"Image: {fits_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to plot {fits_file}: {e}")

        if img_section.figures:
            sections.append(img_section)

    # Generate report
    report_path = output_dir / f"{ms_path.stem}_diagnostic_report.html"
    metadata = ReportMetadata(
        title=f"Diagnostic Report: {ms_path.name}",
        observation_id=ms_path.stem,
    )

    return generate_html_report(sections, report_path, metadata)
