#!/usr/bin/env python3
"""
Analyze test coverage report and identify gaps.

This script parses coverage reports and generates a detailed analysis
of coverage gaps and recommendations.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def parse_coverage_report(report_path: Path) -> Dict:
    """Parse coverage report text output."""
    if not report_path.exists():
        return {"error": "Coverage report not found"}
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Extract total coverage - handle different formats
    # Format 1: TOTAL    2170   1750    19%
    # Format 2: TOTAL                                           2170   1750    19%
    total_match = re.search(r'TOTAL\s+\d+\s+\d+\s+\d+%\s*$', content, re.MULTILINE)
    if not total_match:
        # Try alternative format with more whitespace
        total_match = re.search(r'TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%', content)
    
    if total_match:
        # Extract from the line
        total_line = total_match.group(0) if hasattr(total_match, 'group') else total_match.group(0)
        numbers = re.findall(r'\d+', total_line)
        if len(numbers) >= 3:
            statements = int(numbers[0])
            missing = int(numbers[1])
            percent = float(numbers[2])
            covered = statements - missing
        else:
            return {"error": "Could not parse total coverage"}
    else:
        return {"error": "Total coverage line not found"}
    
    total_coverage = {
        "statements": statements,
        "missing": missing,
        "covered": covered,
        "percent": percent
    }
    
    # Extract module-by-module coverage
    modules = []
    # Pattern: module_name    statements    missing    percent%
    # Handle variable whitespace
    module_pattern = r'^([^\s]+(?:\.[^\s]+)*)\s+(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)%'
    
    for match in re.finditer(module_pattern, content, re.MULTILINE):
        module_name = match.group(1)
        if module_name == "TOTAL" or module_name.startswith("---"):
            continue
        
        try:
            modules.append({
                "name": module_name,
                "statements": int(match.group(2)),
                "missing": int(match.group(3)),
                "percent": float(match.group(4))
            })
        except (ValueError, IndexError):
            continue
    
    # Sort by coverage percentage (lowest first)
    modules.sort(key=lambda x: x["percent"])
    
    return {
        "total": total_coverage,
        "modules": modules
    }

def generate_coverage_analysis(coverage_data: Dict, output_path: Path):
    """Generate coverage analysis document."""
    if "error" in coverage_data:
        return
    
    output_lines = [
        "# Test Coverage Analysis",
        "",
        "> **Generated:** This document is auto-generated from coverage reports.",
        "> **Last Updated:** Run `scripts/analyze_coverage.py` to regenerate.",
        "",
        "## Overall Coverage Summary",
        "",
        f"**Total Coverage:** {coverage_data['total']['percent']:.1f}%",
        "",
        f"- **Statements:** {coverage_data['total']['statements']:,}",
        f"- **Covered:** {coverage_data['total']['covered']:,}",
        f"- **Missing:** {coverage_data['total']['missing']:,}",
        "",
        "## Coverage by Module",
        "",
        "### Low Coverage Modules (< 50%)",
        ""
    ]
    
    low_coverage = [m for m in coverage_data["modules"] if m["percent"] < 50]
    if low_coverage:
        output_lines.append("| Module | Statements | Missing | Coverage % |")
        output_lines.append("|--------|------------|---------|------------|")
        for module in low_coverage[:20]:  # Top 20
            output_lines.append(
                f"| `{module['name']}` | {module['statements']} | "
                f"{module['missing']} | {module['percent']:.1f}% |"
            )
    else:
        output_lines.append("No modules with coverage below 50%.")
    
    output_lines.extend([
        "",
        "### Medium Coverage Modules (50-80%)",
        ""
    ])
    
    medium_coverage = [m for m in coverage_data["modules"] if 50 <= m["percent"] < 80]
    if medium_coverage:
        output_lines.append("| Module | Statements | Missing | Coverage % |")
        output_lines.append("|--------|------------|---------|------------|")
        for module in medium_coverage[:20]:
            output_lines.append(
                f"| `{module['name']}` | {module['statements']} | "
                f"{module['missing']} | {module['percent']:.1f}% |"
            )
    else:
        output_lines.append("No modules with coverage between 50-80%.")
    
    output_lines.extend([
        "",
        "### High Coverage Modules (>= 80%)",
        ""
    ])
    
    high_coverage = [m for m in coverage_data["modules"] if m["percent"] >= 80]
    if high_coverage:
        output_lines.append("| Module | Statements | Missing | Coverage % |")
        output_lines.append("|--------|------------|---------|------------|")
        for module in high_coverage[:20]:
            output_lines.append(
                f"| `{module['name']}` | {module['statements']} | "
                f"{module['missing']} | {module['percent']:.1f}% |"
            )
    else:
        output_lines.append("No modules with coverage above 80%.")
    
    output_lines.extend([
        "",
        "## Recommendations",
        "",
        "### Priority 1: Critical Modules with Low Coverage",
        ""
    ])
    
    critical_modules = [
        "pipeline.orchestrator",
        "pipeline.config",
        "pipeline.stages",
        "calibration.calibration",
        "imaging.spw_imaging",
        "qa.base"
    ]
    
    for module_name in critical_modules:
        module = next((m for m in coverage_data["modules"] if module_name in m["name"]), None)
        if module and module["percent"] < 80:
            output_lines.extend([
                f"- **{module['name']}** ({module['percent']:.1f}% coverage)",
                f"  - Add unit tests for core functionality",
                f"  - Add integration tests for stage interactions",
                ""
            ])
    
    output_lines.extend([
        "### Priority 2: Improve Coverage for Medium Coverage Modules",
        "",
        "Focus on modules with 50-80% coverage that are frequently used:",
        ""
    ])
    
    for module in medium_coverage[:10]:
        output_lines.append(f"- `{module['name']}` - Add tests for edge cases and error handling")
    
    output_lines.extend([
        "",
        "## How to Improve Coverage",
        "",
        "1. **Run coverage report:**",
        "   ```bash",
        "   pytest --cov=src/dsa110_contimg --cov-report=term-missing tests/",
        "   ```",
        "",
        "2. **View HTML report:**",
        "   ```bash",
        "   pytest --cov=src/dsa110_contimg --cov-report=html:tests/coverage_html tests/",
        "   # Open tests/coverage_html/index.html in browser",
        "   ```",
        "",
        "3. **Focus on uncovered lines:**",
        "   - Review uncovered lines in HTML report",
        "   - Add tests for missing branches",
        "   - Test error conditions and edge cases",
        "",
        "4. **Use coverage markers:**",
        "   ```python",
        "   # Mark lines that don't need coverage",
        "   if False:  # pragma: no cover",
        "       debug_code()",
        "   ```",
        "",
        "## Related Documentation",
        "",
        "- [Testing Guide](../docs/how-to/testing.md)",
        "- [Pipeline Stage Architecture](../docs/concepts/pipeline_stage_architecture.md)",
        ""
    ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))
    
    print(f"Generated coverage analysis: {output_path}")

if __name__ == "__main__":
    # Try full coverage report first, fall back to pipeline coverage
    report_path = Path("/tmp/coverage_report.txt")
    pipeline_report_path = Path("/tmp/coverage_pipeline.txt")
    output_path = Path(__file__).parent.parent / "docs" / "reference" / "test_coverage_analysis.md"
    
    coverage_data = parse_coverage_report(report_path)
    if "error" in coverage_data or coverage_data["total"]["statements"] == 0:
        # Try pipeline coverage as fallback
        print("Full coverage report not ready, using pipeline coverage...", file=sys.stderr)
        coverage_data = parse_coverage_report(pipeline_report_path)
    
    if "error" not in coverage_data and coverage_data["total"]["statements"] > 0:
        generate_coverage_analysis(coverage_data, output_path)
    else:
        print(f"Error: Could not parse coverage report", file=sys.stderr)
        sys.exit(1)

