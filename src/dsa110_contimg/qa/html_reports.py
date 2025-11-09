"""
HTML report generation for validation results.

Generates comprehensive HTML validation reports similar to ASKAP's validation
framework, with pass/fail indicators, tables, and integrated visualization.
"""

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from astropy.io import fits

from dsa110_contimg.qa.catalog_validation import CatalogValidationResult
from dsa110_contimg.qa.validation_plots import (
    plot_astrometry_scatter,
    plot_flux_ratio_histogram,
    plot_completeness_curve
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Unified validation report combining all tests."""

    image_path: str
    image_name: str
    astrometry: Optional[CatalogValidationResult] = None
    flux_scale: Optional[CatalogValidationResult] = None
    source_counts: Optional[CatalogValidationResult] = None

    # Overall assessment
    overall_status: str = "UNKNOWN"  # "PASS", "FAIL", "WARNING", "UNKNOWN"
    score: float = 0.0  # 0.0 to 1.0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Metadata
    generated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    catalog_used: str = "nvss"

    def __post_init__(self):
        """Calculate overall status and score after initialization."""
        if self.astrometry or self.flux_scale or self.source_counts:
            self._calculate_overall_status()

    def _calculate_overall_status(self) -> None:
        """Calculate overall validation status and score."""
        all_issues = []
        all_warnings = []
        scores = []

        # Collect issues and warnings from all tests
        if self.astrometry:
            all_issues.extend(self.astrometry.issues)
            all_warnings.extend(self.astrometry.warnings)
            scores.append(0.0 if self.astrometry.has_issues else (
                0.7 if self.astrometry.has_warnings else 1.0))

        if self.flux_scale:
            all_issues.extend(self.flux_scale.issues)
            all_warnings.extend(self.flux_scale.warnings)
            scores.append(0.0 if self.flux_scale.has_issues else (
                0.7 if self.flux_scale.has_warnings else 1.0))

        if self.source_counts:
            all_issues.extend(self.source_counts.issues)
            all_warnings.extend(self.source_counts.warnings)
            scores.append(0.0 if self.source_counts.has_issues else (
                0.7 if self.source_counts.has_warnings else 1.0))

        self.issues = all_issues
        self.warnings = all_warnings

        # Calculate overall score (weighted average)
        if scores:
            self.score = float(np.mean(scores))
        else:
            self.score = 0.0

        # Determine overall status
        if len(all_issues) > 0:
            self.overall_status = "FAIL"
        elif len(all_warnings) > 0:
            self.overall_status = "WARNING"
        elif len(scores) > 0 and all(s >= 0.9 for s in scores):
            self.overall_status = "PASS"
        else:
            self.overall_status = "WARNING"


def _get_status_color(status: str) -> str:
    """Get color code for status."""
    colors = {
        "PASS": "#28a745",  # Green
        "WARNING": "#ffc107",  # Yellow/Orange
        "FAIL": "#dc3545",  # Red
        "UNKNOWN": "#6c757d",  # Gray
    }
    return colors.get(status.upper(), "#6c757d")


def _get_status_icon(status: str) -> str:
    """Get icon for status."""
    icons = {
        "PASS": "✓",
        "WARNING": "⚠",
        "FAIL": "✗",
        "UNKNOWN": "?",
    }
    return icons.get(status.upper(), "?")


def _format_float(value: Optional[float], precision: int = 3, unit: str = "") -> str:
    """Format float value for display."""
    if value is None:
        return "N/A"
    if not np.isfinite(value):
        return "N/A"
    formatted = f"{value:.{precision}f}"
    return f"{formatted} {unit}".strip() if unit else formatted


def _generate_astrometry_section(result: CatalogValidationResult) -> str:
    """Generate HTML section for astrometry validation."""
    status_color = _get_status_color(
        "PASS" if not result.has_issues else "FAIL")
    status_icon = _get_status_icon("PASS" if not result.has_issues else "FAIL")

    html = f"""
    <div class="validation-section">
        <h3>Astrometry Validation</h3>
        <div class="status-badge" style="background-color: {status_color};">
            {status_icon} {result.validation_type.upper()}
        </div>
        
        <table class="metrics-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Catalog Used</td>
                <td>{result.catalog_used.upper()}</td>
            </tr>
            <tr>
                <td>Sources Detected</td>
                <td>{result.n_detected}</td>
            </tr>
            <tr>
                <td>Catalog Sources</td>
                <td>{result.n_catalog}</td>
            </tr>
            <tr>
                <td>Matched Sources</td>
                <td>{result.n_matched}</td>
            </tr>
            <tr>
                <td>Mean Offset</td>
                <td>{_format_float(result.mean_offset_arcsec, 2, "arcsec")}</td>
            </tr>
            <tr>
                <td>RMS Offset</td>
                <td>{_format_float(result.rms_offset_arcsec, 2, "arcsec")}</td>
            </tr>
            <tr>
                <td>Max Offset</td>
                <td>{_format_float(result.max_offset_arcsec, 2, "arcsec")}</td>
            </tr>
            <tr>
                <td>RA Offset</td>
                <td>{_format_float(result.offset_ra_arcsec, 2, "arcsec")}</td>
            </tr>
            <tr>
                <td>Dec Offset</td>
                <td>{_format_float(result.offset_dec_arcsec, 2, "arcsec")}</td>
            </tr>
        </table>
    """

    # Add astrometry plot if available
    plot_img = plot_astrometry_scatter(result)
    if plot_img:
        html += f"""
        <h4>Astrometry Visualization</h4>
        <div style="text-align: center; margin: 20px 0;">
            <img src="{plot_img}" alt="Astrometry scatter plot" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px;">
        </div>
        """

    if result.issues:
        html += '<div class="issues"><h4>Issues:</h4><ul>'
        for issue in result.issues:
            html += f'<li>{issue}</li>'
        html += '</ul></div>'

    if result.warnings:
        html += '<div class="warnings"><h4>Warnings:</h4><ul>'
        for warning in result.warnings:
            html += f'<li>{warning}</li>'
        html += '</ul></div>'

    html += '</div>'
    return html


def _generate_flux_scale_section(result: CatalogValidationResult) -> str:
    """Generate HTML section for flux scale validation."""
    status_color = _get_status_color(
        "PASS" if not result.has_issues else "FAIL")
    status_icon = _get_status_icon("PASS" if not result.has_issues else "FAIL")

    html = f"""
    <div class="validation-section">
        <h3>Flux Scale Validation</h3>
        <div class="status-badge" style="background-color: {status_color};">
            {status_icon} {result.validation_type.upper()}
        </div>
        
        <table class="metrics-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Catalog Used</td>
                <td>{result.catalog_used.upper()}</td>
            </tr>
            <tr>
                <td>Valid Measurements</td>
                <td>{result.n_matched}</td>
            </tr>
            <tr>
                <td>Catalog Sources</td>
                <td>{result.n_catalog}</td>
            </tr>
            <tr>
                <td>Mean Flux Ratio</td>
                <td>{_format_float(result.mean_flux_ratio, 3)}</td>
            </tr>
            <tr>
                <td>RMS Flux Ratio</td>
                <td>{_format_float(result.rms_flux_ratio, 3)}</td>
            </tr>
            <tr>
                <td>Flux Scale Error</td>
                <td>{_format_float(result.flux_scale_error, 3)} ({_format_float(result.flux_scale_error * 100 if result.flux_scale_error else None, 1, "%")})</td>
            </tr>
        </table>
    """

    # Add flux ratio plot if available
    plot_img = plot_flux_ratio_histogram(result)
    if plot_img:
        html += f"""
        <h4>Flux Scale Visualization</h4>
        <div style="text-align: center; margin: 20px 0;">
            <img src="{plot_img}" alt="Flux ratio histogram" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px;">
        </div>
        """

    if result.issues:
        html += '<div class="issues"><h4>Issues:</h4><ul>'
        for issue in result.issues:
            html += f'<li>{issue}</li>'
        html += '</ul></div>'

    if result.warnings:
        html += '<div class="warnings"><h4>Warnings:</h4><ul>'
        for warning in result.warnings:
            html += f'<li>{warning}</li>'
        html += '</ul></div>'

    html += '</div>'
    return html


def _generate_source_counts_section(result: CatalogValidationResult) -> str:
    """Generate HTML section for source counts validation."""
    status_color = _get_status_color(
        "PASS" if not result.has_issues else "FAIL")
    status_icon = _get_status_icon("PASS" if not result.has_issues else "FAIL")

    html = f"""
    <div class="validation-section">
        <h3>Source Counts Validation</h3>
        <div class="status-badge" style="background-color: {status_color};">
            {status_icon} {result.validation_type.upper()}
        </div>
        
        <table class="metrics-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Catalog Used</td>
                <td>{result.catalog_used.upper()}</td>
            </tr>
            <tr>
                <td>Sources Detected</td>
                <td>{result.n_detected}</td>
            </tr>
            <tr>
                <td>Catalog Sources</td>
                <td>{result.n_catalog}</td>
            </tr>
            <tr>
                <td>Matched Sources</td>
                <td>{result.n_matched}</td>
            </tr>
            <tr>
                <td>Overall Completeness</td>
                <td>{_format_float(result.completeness, 1, "%") if result.completeness is not None else "N/A"}</td>
            </tr>
            <tr>
                <td>Completeness Limit</td>
                <td>{_format_float(result.completeness_limit_jy * 1000, 2, " mJy") if result.completeness_limit_jy is not None else "N/A"}</td>
            </tr>
        </table>
    """

    # Add completeness per bin table if available
    if (result.completeness_bins_jy and result.completeness_per_bin and
            result.catalog_counts_per_bin and result.detected_counts_per_bin):
        html += """
        <h4>Completeness by Flux Density</h4>
        <table class="metrics-table">
            <tr>
                <th>Flux Density (mJy)</th>
                <th>Catalog Sources</th>
                <th>Detected Sources</th>
                <th>Completeness</th>
            </tr>
        """
        for i, (bin_center, catalog_count, detected_count, completeness) in enumerate(zip(
            result.completeness_bins_jy,
            result.catalog_counts_per_bin,
            result.detected_counts_per_bin,
            result.completeness_per_bin
        )):
            if catalog_count > 0:  # Only show bins with catalog sources
                completeness_pct = completeness * 100
                # Color code completeness
                if completeness_pct >= 95:
                    completeness_color = "#28a745"  # Green
                elif completeness_pct >= 80:
                    completeness_color = "#ffc107"  # Yellow
                else:
                    completeness_color = "#dc3545"  # Red

                html += f"""
            <tr>
                <td>{_format_float(bin_center * 1000, 2)}</td>
                <td>{catalog_count}</td>
                <td>{detected_count}</td>
                <td style="color: {completeness_color}; font-weight: bold;">
                    {_format_float(completeness, 1, "%")}
                </td>
            </tr>
                """
        html += "</table>"

    # Add completeness plot if available
    plot_img = plot_completeness_curve(result)
    if plot_img:
        html += f"""
        <h4>Completeness Visualization</h4>
        <div style="text-align: center; margin: 20px 0;">
            <img src="{plot_img}" alt="Completeness curve" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px;">
        </div>
        """

    if result.issues:
        html += '<div class="issues"><h4>Issues:</h4><ul>'
        for issue in result.issues:
            html += f'<li>{issue}</li>'
        html += '</ul></div>'

    if result.warnings:
        html += '<div class="warnings"><h4>Warnings:</h4><ul>'
        for warning in result.warnings:
            html += f'<li>{warning}</li>'
        html += '</ul></div>'

    html += '</div>'
    return html


def _get_image_metadata(image_path: str) -> Dict[str, str]:
    """Extract basic metadata from image."""
    try:
        with fits.open(image_path) as hdul:
            header = hdul[0].header

            metadata = {
                "filename": Path(image_path).name,
                "size": f"{Path(image_path).stat().st_size / (1024*1024):.2f} MB",
            }

            # Try to get frequency
            if "RESTFRQ" in header:
                metadata["frequency"] = f"{header['RESTFRQ']:.3f} GHz"
            elif "FREQ" in header:
                metadata["frequency"] = f"{header['FREQ']:.3f} GHz"

            # Try to get image dimensions
            if "NAXIS1" in header and "NAXIS2" in header:
                metadata["dimensions"] = f"{header['NAXIS1']} × {header['NAXIS2']} pixels"

            # Try to get pixel scale
            if "CDELT1" in header:
                cell_size = abs(header["CDELT1"]) * 3600  # Convert to arcsec
                metadata["cell_size"] = f"{cell_size:.2f} arcsec/pixel"

            return metadata
    except Exception as e:
        logger.warning(f"Could not extract image metadata: {e}")
        return {"filename": Path(image_path).name}


def generate_html_report(
    report: ValidationReport,
    output_path: Optional[str] = None,
    include_plots: bool = False
) -> str:
    """
    Generate comprehensive HTML validation report.

    Args:
        report: ValidationReport with all validation results
        output_path: Optional path to save HTML file
        include_plots: Whether to include embedded plots (future enhancement)

    Returns:
        HTML content as string
    """
    status_color = _get_status_color(report.overall_status)
    status_icon = _get_status_icon(report.overall_status)

    # Get image metadata
    image_metadata = _get_image_metadata(report.image_path)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DSA-110 Validation Report: {report.image_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .summary {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h2 {{
            margin-top: 0;
            color: #667eea;
        }}
        .status-overall {{
            display: inline-block;
            padding: 15px 30px;
            border-radius: 6px;
            font-size: 1.2em;
            font-weight: bold;
            color: white;
            background-color: {status_color};
            margin: 10px 0;
        }}
        .score {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .metadata-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .metadata-table th,
        .metadata-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .metadata-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        .validation-section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .validation-section h3 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
            margin-bottom: 15px;
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .metrics-table th,
        .metrics-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        .metrics-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        .metrics-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .issues {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .issues h4 {{
            margin-top: 0;
            color: #856404;
        }}
        .issues ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .issues li {{
            margin: 5px 0;
        }}
        .warnings {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .warnings h4 {{
            margin-top: 0;
            color: #856404;
        }}
        .warnings ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .warnings li {{
            margin: 5px 0;
        }}
        .footer {{
            text-align: center;
            color: #6c757d;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>DSA-110 Continuum Imaging Validation Report</h1>
        <p><strong>Image:</strong> {report.image_name}</p>
        <p><strong>Generated:</strong> {report.generated_at}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <div class="status-overall">
            {status_icon} Overall Status: {report.overall_status}
        </div>
        <div class="score">
            Validation Score: {report.score:.1%}
        </div>
        
        <table class="metadata-table">
            <tr>
                <th>Property</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Image Path</td>
                <td><code>{report.image_path}</code></td>
            </tr>
"""

    # Add image metadata
    for key, value in image_metadata.items():
        html += f"""
            <tr>
                <td>{key.replace('_', ' ').title()}</td>
                <td>{value}</td>
            </tr>
"""

    html += f"""
            <tr>
                <td>Catalog Used</td>
                <td>{report.catalog_used.upper()}</td>
            </tr>
        </table>
"""

    # Add overall issues and warnings
    if report.issues:
        html += """
        <div class="issues">
            <h4>Overall Issues:</h4>
            <ul>
"""
        for issue in report.issues:
            html += f'                <li>{issue}</li>\n'
        html += """            </ul>
        </div>
"""

    if report.warnings:
        html += """
        <div class="warnings">
            <h4>Overall Warnings:</h4>
            <ul>
"""
        for warning in report.warnings:
            html += f'                <li>{warning}</li>\n'
        html += """            </ul>
        </div>
"""

    html += """    </div>
"""

    # Add validation sections
    if report.astrometry:
        html += _generate_astrometry_section(report.astrometry)

    if report.flux_scale:
        html += _generate_flux_scale_section(report.flux_scale)

    if report.source_counts:
        html += _generate_source_counts_section(report.source_counts)

    # Footer
    html += f"""
    <div class="footer">
        <p>Generated by DSA-110 Continuum Imaging Pipeline</p>
        <p>Report generated at {report.generated_at}</p>
    </div>
</body>
</html>
"""

    # Save to file if output path provided
    if output_path:
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path_obj, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"HTML validation report saved to {output_path}")

    return html


def generate_validation_report(
    image_path: str,
    astrometry_result: Optional[CatalogValidationResult] = None,
    flux_scale_result: Optional[CatalogValidationResult] = None,
    source_counts_result: Optional[CatalogValidationResult] = None,
    output_path: Optional[str] = None,
    catalog: str = "nvss"
) -> ValidationReport:
    """
    Generate unified validation report from validation results.

    Args:
        image_path: Path to validated image
        astrometry_result: Optional astrometry validation result
        flux_scale_result: Optional flux scale validation result
        source_counts_result: Optional source counts validation result
        output_path: Optional path to save HTML report
        catalog: Catalog used for validation

    Returns:
        ValidationReport object
    """
    image_name = Path(image_path).name

    report = ValidationReport(
        image_path=image_path,
        image_name=image_name,
        astrometry=astrometry_result,
        flux_scale=flux_scale_result,
        source_counts=source_counts_result,
        catalog_used=catalog
    )

    # Generate HTML if output path provided
    if output_path:
        generate_html_report(report, output_path=output_path)

    return report
