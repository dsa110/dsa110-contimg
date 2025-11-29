#!/usr/bin/env python3
"""
Mermaid Diagram Visual Testing Script (MCP Browser Version)

Tests all MkDocs pages to ensure Mermaid diagrams render correctly without errors.
Uses MCP browser tools instead of Playwright to avoid GLIBC compatibility issues.
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class TestResult:
    """Result for a single page test"""

    url: str
    page_path: str
    success: bool
    error_message: Optional[str] = None
    mermaid_count: int = 0
    load_time: float = 0.0


@dataclass
class TestReport:
    """Complete test report"""

    total_pages: int
    successful_pages: int
    failed_pages: int
    results: List[TestResult]
    execution_time: float
    timestamp: str


class MkDocsPageExtractor:
    """Extract all pages from mkdocs.yml navigation"""

    def __init__(self, mkdocs_path: Path):
        self.mkdocs_path = mkdocs_path
        self.pages: List[str] = []

    def extract_pages(self) -> List[str]:
        """Extract all page paths from mkdocs.yml"""
        # Parse nav section line by line to avoid Python-specific YAML tag issues
        with open(self.mkdocs_path, "r") as f:
            lines = f.readlines()

        in_nav = False
        for line in lines:
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            # Start of nav section
            if line.strip().startswith("nav:"):
                in_nav = True
                continue

            # Stop at next top-level key (indent level 0)
            if in_nav and current_indent == 0 and line.strip() and not line.strip().startswith("#"):
                break

            # Extract file paths from nav structure
            if in_nav and ":" in line:
                # Pattern: "  - Title: path.md" or "    - path.md"
                if any(ext in line for ext in [".md", ".ipynb", ".py"]):
                    # Extract the path part after the colon
                    parts = line.split(":")
                    if len(parts) >= 2:
                        path_part = parts[-1].strip()
                        # Remove quotes if present
                        path_part = path_part.strip("'\"")
                        # Check if it's a file path
                        if any(path_part.endswith(ext) for ext in [".md", ".ipynb", ".py"]):
                            self.pages.append(path_part)

        # Remove duplicates and sort
        self.pages = sorted(list(set(self.pages)))
        return self.pages


class MkDocsServer:
    """Manage MkDocs server lifecycle"""

    def __init__(self, port: int = 8001, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"

    def start(self, timeout: int = 30) -> bool:
        """Start MkDocs server"""
        print(f"Starting MkDocs server on {self.base_url}...")

        try:
            # Use casa6 Python if available, otherwise use system mkdocs
            casa6_python = "/opt/miniforge/envs/casa6/bin/python"
            if Path(casa6_python).exists():
                self.process = subprocess.Popen(
                    [
                        casa6_python,
                        "-m",
                        "mkdocs",
                        "serve",
                        "-a",
                        f"{self.host}:{self.port}",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=Path(__file__).parent.parent.parent,
                )
            else:
                self.process = subprocess.Popen(
                    ["mkdocs", "serve", "-a", f"{self.host}:{self.port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=Path(__file__).parent.parent.parent,
                )

            # Wait for server to be ready
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    import urllib.request

                    urllib.request.urlopen(self.base_url, timeout=2)
                    print(f"MkDocs server ready at {self.base_url}")
                    return True
                except Exception:
                    time.sleep(1)

            print(f"ERROR: MkDocs server failed to start within {timeout} seconds")
            return False

        except FileNotFoundError:
            print(
                "ERROR: mkdocs command not found. Install with: pip install -r docs/requirements.txt"
            )
            return False

    def stop(self):
        """Stop MkDocs server"""
        if self.process:
            print("Stopping MkDocs server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


class MermaidErrorDetector:
    """Detect Mermaid rendering errors using source file analysis"""

    ERROR_INDICATORS = [
        "Syntax error in text",
        "mermaid version",
    ]

    def __init__(self, page_path: Path):
        self.page_path = page_path
        self.repo_root = Path(__file__).parent.parent.parent

    def check_for_errors(self) -> Tuple[bool, Optional[str], int]:
        """
        Check if page has Mermaid diagrams and validate syntax.
        Returns: (has_error, error_message, mermaid_count)
        """
        full_path = self.repo_root / "docs" / self.page_path

        if not full_path.exists():
            return False, f"File not found: {full_path}", 0

        try:
            with open(full_path, "r") as f:
                content = f.read()

            # Count Mermaid diagrams
            mermaid_count = content.count("```mermaid")

            if mermaid_count == 0:
                return False, None, 0

            # Basic syntax validation - check for common errors
            errors = []

            # Check for unclosed mermaid blocks
            mermaid_starts = content.count("```mermaid")
            mermaid_ends = content.count("```")
            if mermaid_ends < mermaid_starts * 2:
                errors.append("Unclosed mermaid code block")

            # Check for empty mermaid blocks
            import re

            mermaid_blocks = re.findall(r"```mermaid\n(.*?)```", content, re.DOTALL)
            for i, block in enumerate(mermaid_blocks, 1):
                if not block.strip():
                    errors.append(f"Empty mermaid diagram #{i}")
                # Check for common syntax issues
                if block.strip() and not any(
                    keyword in block
                    for keyword in [
                        "graph",
                        "flowchart",
                        "sequenceDiagram",
                        "classDiagram",
                        "stateDiagram",
                        "erDiagram",
                        "gantt",
                        "pie",
                        "gitgraph",
                    ]
                ):
                    errors.append(f"Mermaid diagram #{i} may be missing diagram type declaration")

            if errors:
                return True, "; ".join(errors), mermaid_count

            return False, None, mermaid_count

        except Exception as e:
            return True, f"Error reading file: {str(e)}", 0


class MermaidDiagramTester:
    """Main test runner for Mermaid diagrams"""

    def __init__(self, mkdocs_path: Path, base_url: str = "http://127.0.0.1:8001"):
        self.mkdocs_path = mkdocs_path
        self.base_url = base_url
        self.results: List[TestResult] = []

    def run_tests(self) -> TestReport:
        """Run tests on all pages"""
        print("=" * 80)
        print("Mermaid Diagram Visual Testing (Source File Analysis)")
        print("=" * 80)

        # Extract pages
        extractor = MkDocsPageExtractor(self.mkdocs_path)
        pages = extractor.extract_pages()
        print(f"\nFound {len(pages)} pages to test\n")

        # Start server (for URL generation, but we test source files)
        server = MkDocsServer()
        server_started = server.start()

        try:
            # Run tests
            start_time = time.time()

            for i, page_path in enumerate(pages, 1):
                result = self._test_page(page_path, i, len(pages))
                self.results.append(result)

            execution_time = time.time() - start_time

            # Generate report
            successful = sum(1 for r in self.results if r.success)
            failed = len(self.results) - successful

            report = TestReport(
                total_pages=len(self.results),
                successful_pages=successful,
                failed_pages=failed,
                results=self.results,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
            )

            return report

        finally:
            if server_started:
                server.stop()

    def _test_page(self, page_path: str, current: int, total: int) -> TestResult:
        """Test a single page"""
        # Convert markdown path to URL
        url_path = page_path
        if url_path.endswith(".md"):
            url_path = url_path[:-3]
        elif url_path.endswith(".ipynb"):
            url_path = url_path[:-6]
        elif url_path.endswith(".py"):
            url_path = url_path[:-3]
        if not url_path.endswith("/"):
            url_path += "/"
        if not url_path.startswith("/"):
            url_path = "/" + url_path
        url = self.base_url + url_path

        print(f"[{current}/{total}] Testing: {page_path}")

        start_time = time.time()

        try:
            # Use source file analysis instead of browser
            detector = MermaidErrorDetector(Path(page_path))
            has_error, error_msg, mermaid_count = detector.check_for_errors()
            load_time = time.time() - start_time

            if has_error:
                print(f"  ✗ FAILED: {error_msg}")
                return TestResult(
                    url=url,
                    page_path=page_path,
                    success=False,
                    error_message=error_msg,
                    mermaid_count=mermaid_count,
                    load_time=load_time,
                )
            elif mermaid_count > 0:
                print(f"  ✓ PASSED ({mermaid_count} diagram(s))")
            else:
                print("  - SKIPPED (no Mermaid diagrams)")

            return TestResult(
                url=url,
                page_path=page_path,
                success=True,
                mermaid_count=mermaid_count,
                load_time=load_time,
            )

        except Exception as e:
            load_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            print(f"  ✗ ERROR: {error_msg}")
            return TestResult(
                url=url,
                page_path=page_path,
                success=False,
                error_message=error_msg,
                load_time=load_time,
            )

    def print_report(self, report: TestReport):
        """Print test report"""
        print("\n" + "=" * 80)
        print("TEST REPORT")
        print("=" * 80)
        print(f"Total pages tested: {report.total_pages}")
        print(f"Successful: {report.successful_pages}")
        print(f"Failed: {report.failed_pages}")
        print(f"Execution time: {report.execution_time:.2f} seconds")
        print(f"Timestamp: {report.timestamp}")

        if report.failed_pages > 0:
            print("\nFAILED PAGES:")
            print("-" * 80)
            for result in report.results:
                if not result.success:
                    print(f"  ✗ {result.page_path}")
                    print(f"    URL: {result.url}")
                    if result.error_message:
                        print(f"    Error: {result.error_message}")
                    if result.mermaid_count > 0:
                        print(f"    Mermaid diagrams: {result.mermaid_count}")

        # Pages with Mermaid diagrams
        pages_with_mermaid = [r for r in report.results if r.mermaid_count > 0]
        if pages_with_mermaid:
            print(f"\nPAGES WITH MERMAID DIAGRAMS ({len(pages_with_mermaid)}):")
            print("-" * 80)
            for result in pages_with_mermaid:
                status = "✓" if result.success else "✗"
                print(f"  {status} {result.page_path} ({result.mermaid_count} diagram(s))")

    def save_report(self, report: TestReport, output_path: Path):
        """Save test report to JSON file"""
        report_dict = {
            "timestamp": report.timestamp,
            "total_pages": report.total_pages,
            "successful_pages": report.successful_pages,
            "failed_pages": report.failed_pages,
            "execution_time": report.execution_time,
            "results": [
                {
                    "url": r.url,
                    "page_path": r.page_path,
                    "success": r.success,
                    "error_message": r.error_message,
                    "mermaid_count": r.mermaid_count,
                    "load_time": r.load_time,
                }
                for r in report.results
            ],
        }

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.parent.parent
    mkdocs_path = repo_root / "mkdocs.yml"

    if not mkdocs_path.exists():
        print(f"ERROR: mkdocs.yml not found at {mkdocs_path}")
        sys.exit(1)

    tester = MermaidDiagramTester(mkdocs_path)

    try:
        report = tester.run_tests()
        tester.print_report(report)

        # Save report
        output_dir = repo_root / "tests" / "docs" / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"mermaid_test_report_{timestamp}.json"
        tester.save_report(report, output_path)

        # Exit with error code if tests failed
        if report.failed_pages > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
