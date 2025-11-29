#!/usr/bin/env python3
"""
Documentation Audit Tool

Analyzes markdown files to identify potentially outdated documentation by:
- Finding references to moved/deleted files
- Detecting old code patterns vs current implementation
- Identifying stale date references
- Checking for broken internal links
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DocumentationAuditor:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.all_files = set()
        self.issues = []

    def scan_codebase(self):
        """Build an index of all files in the codebase."""
        print(":file_folder: Scanning codebase structure...")
        for path in self.root_dir.rglob("*"):
            if path.is_file() and not self._should_ignore(path):
                rel_path = path.relative_to(self.root_dir)
                self.all_files.add(str(rel_path))
        print(f"   Found {len(self.all_files)} files")

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [
            "__pycache__",
            ".pyc",
            ".git",
            "node_modules",
            ".egg-info",
            ".pytest_cache",
            ".venv",
            "venv",
        ]
        return any(pattern in str(path) for pattern in ignore_patterns)

    def audit_documentation(self) -> List[Dict]:
        """Audit all markdown files."""
        print("\n:memo: Auditing documentation files...")

        md_files = list(self.root_dir.rglob("*.md"))
        print(f"   Found {len(md_files)} markdown files")

        for md_file in md_files:
            try:
                self._audit_file(md_file)
            except Exception as e:
                self.issues.append(
                    {
                        "file": str(md_file.relative_to(self.root_dir)),
                        "type": "error",
                        "message": f"Failed to audit: {e}",
                    }
                )

        return self.issues

    def _audit_file(self, md_file: Path):
        """Audit a single markdown file."""
        content = md_file.read_text(errors="ignore")
        rel_path = str(md_file.relative_to(self.root_dir))

        # Check for date references that might indicate staleness
        self._check_dates(content, rel_path)

        # Check for file references
        self._check_file_references(content, rel_path, md_file)

        # Check for code blocks with imports
        self._check_code_blocks(content, rel_path)

        # Check for TODO/FIXME markers
        self._check_markers(content, rel_path)

    def _check_dates(self, content: str, file_path: str):
        """Check for date references that might indicate staleness."""
        # Look for explicit date patterns
        date_patterns = [
            r"(?:Last updated|Updated|As of|Date):\s*(\d{4}-\d{2}-\d{2})",
            r"(?:Last updated|Updated|As of|Date):\s*(\w+ \d{1,2},? \d{4})",
        ]

        for pattern in date_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                try:
                    # Try to parse the date
                    if "-" in date_str:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        date = datetime.strptime(date_str, "%B %d, %Y")

                    # Flag if older than 6 months
                    age_days = (datetime.now() - date).days
                    if age_days > 180:
                        self.issues.append(
                            {
                                "file": file_path,
                                "type": "stale_date",
                                "severity": "medium" if age_days > 365 else "low",
                                "message": f'Documentation date is {age_days} days old: "{date_str}"',
                                "line": content[: match.start()].count("\n") + 1,
                            }
                        )
                except ValueError:
                    pass

    def _check_file_references(self, content: str, file_path: str, md_file: Path):
        """Check for references to files that may have moved or been deleted."""
        # Find file path references
        patterns = [
            r"`([^`]+\.(?:py|js|ts|yaml|yml|json|sh))`",  # Inline code
            r"\[([^\]]+)\]\(([^)]+)\)",  # Markdown links
            r"(?:^|\s)((?:dsa110_contimg|scripts|examples)/[^\s\)]+)",  # Direct paths
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                # Extract the path
                if pattern.startswith(r"\["):  # Markdown link
                    ref_path = match.group(2)
                else:
                    ref_path = match.group(1)

                # Skip URLs and anchors
                if ref_path.startswith(("http://", "https://", "#", "mailto:")):
                    continue

                # Check if file exists
                self._verify_file_reference(ref_path, file_path, md_file, match)

    def _verify_file_reference(self, ref_path: str, doc_file: str, md_file_path: Path, match):
        """Verify a single file reference."""
        # Try to resolve the path
        if ref_path.startswith("/"):
            # Absolute from root
            check_path = self.root_dir / ref_path.lstrip("/")
        elif ref_path.startswith(("./", "../")):
            # Relative to document
            check_path = (md_file_path.parent / ref_path).resolve()
        else:
            # Try as relative to root
            check_path = self.root_dir / ref_path

        # Check if exists
        if not check_path.exists():
            # Try to find similar files
            basename = os.path.basename(ref_path)
            similar = [f for f in self.all_files if basename in f]

            suggestion = f" (similar files: {', '.join(similar[:3])})" if similar else ""

            self.issues.append(
                {
                    "file": doc_file,
                    "type": "broken_reference",
                    "severity": "high",
                    "message": f'Referenced file not found: "{ref_path}"{suggestion}',
                    "line": match.string[: match.start()].count("\n") + 1,
                }
            )

    def _check_code_blocks(self, content: str, file_path: str):
        """Check code blocks for outdated import patterns."""
        code_blocks = re.finditer(r"```python\n(.*?)```", content, re.DOTALL)

        for block in code_blocks:
            code = block.group(1)

            # Look for import statements
            imports = re.findall(r"^(?:from|import)\s+([^\s]+)", code, re.MULTILINE)

            for imp in imports:
                # Check if this module exists in codebase
                module_path = imp.replace(".", "/") + ".py"

                # Check common patterns
                if imp.startswith("dsa110_contimg."):
                    module_file = (
                        imp.replace(".", "/").replace("dsa110_contimg", "dsa110_contimg", 1) + ".py"
                    )

                    if not any(module_file in f for f in self.all_files):
                        self.issues.append(
                            {
                                "file": file_path,
                                "type": "outdated_import",
                                "severity": "medium",
                                "message": f"Code example imports non-existent module: {imp}",
                                "line": content[: block.start()].count("\n")
                                + code[: code.find(imp)].count("\n")
                                + 1,
                            }
                        )

    def _check_markers(self, content: str, file_path: str):
        """Check for documentation markers like TODO, FIXME, etc."""
        markers = ["TODO", "FIXME", "XXX", "HACK", "DEPRECATED", "OUTDATED"]

        for marker in markers:
            pattern = rf"\b{marker}\b:?\s*(.{{0,80}})"
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                self.issues.append(
                    {
                        "file": file_path,
                        "type": "documentation_marker",
                        "severity": "low",
                        "message": f"{marker}: {match.group(1).strip()}",
                        "line": content[: match.start()].count("\n") + 1,
                    }
                )

    def generate_report(self, output_file: str = None):
        """Generate a report of issues found."""
        # Group by severity
        by_severity = {"high": [], "medium": [], "low": [], "error": []}

        for issue in self.issues:
            severity = issue.get("severity", "low")
            by_severity[severity].append(issue)

        # Print summary
        print("\n" + "=" * 70)
        print(":bar_chart: DOCUMENTATION AUDIT REPORT")
        print("=" * 70)

        print(f"\n:large_red_circle: High Priority Issues: {len(by_severity['high'])}")
        for issue in by_severity["high"][:10]:  # Show first 10
            print(f"   • {issue['file']}:{issue.get('line', '?')} - {issue['message']}")

        print(f"\n🟡 Medium Priority Issues: {len(by_severity['medium'])}")
        for issue in by_severity["medium"][:10]:
            print(f"   • {issue['file']}:{issue.get('line', '?')} - {issue['message']}")

        print(f"\n🟢 Low Priority Issues: {len(by_severity['low'])}")
        print(f"   (Documentation markers, old dates, etc.)")

        # Save detailed report
        if output_file:
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "total_issues": len(self.issues),
                "by_severity": {
                    "high": len(by_severity["high"]),
                    "medium": len(by_severity["medium"]),
                    "low": len(by_severity["low"]),
                },
                "issues": self.issues,
            }

            output_path = Path(output_file)
            output_path.write_text(json.dumps(report_data, indent=2))
            print(f"\n:floppy_disk: Detailed report saved to: {output_file}")

        return by_severity


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Audit documentation for outdated content")
    parser.add_argument(
        "--root", default="/data/dsa110-contimg/backend/src", help="Root directory of the project"
    )
    parser.add_argument(
        "--output", default="documentation_audit.json", help="Output file for detailed report"
    )

    args = parser.parse_args()

    auditor = DocumentationAuditor(args.root)
    auditor.scan_codebase()
    auditor.audit_documentation()
    auditor.generate_report(args.output)


if __name__ == "__main__":
    main()
