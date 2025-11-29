#!/usr/bin/env python3
"""
Refactor Impact Analyzer

Helps identify impact of refactoring by:
- Finding all imports of moved/renamed modules
- Detecting call sites of refactored functions/classes
- Generating a migration checklist
- Identifying test coverage gaps
"""

import ast
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class RefactorAnalyzer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.python_files = []
        self.imports = defaultdict(list)  # module -> files that import it
        self.definitions = defaultdict(list)  # name -> files that define it
        self.usages = defaultdict(list)  # name -> files that use it

    def scan(self):
        """Scan all Python files in the codebase."""
        print(":left-pointing_magnifying_glass: Scanning Python files...")

        for path in self.root_dir.rglob("*.py"):
            if self._should_ignore(path):
                continue

            self.python_files.append(path)

        print(f"   Found {len(self.python_files)} Python files")

        # Analyze each file
        print("\n:bar_chart: Analyzing imports and definitions...")
        for i, py_file in enumerate(self.python_files):
            if (i + 1) % 50 == 0:
                print(f"   Progress: {i+1}/{len(self.python_files)}")

            try:
                self._analyze_file(py_file)
            except Exception as e:
                print(f"   :warning_sign::variation_selector-16:  Failed to analyze {py_file}: {e}")

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [
            "__pycache__",
            ".pyc",
            "test_",
            "_test.py",
            ".pytest_cache",
            ".venv",
            "venv",
            ".egg-info",
        ]
        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)

    def _analyze_file(self, py_file: Path):
        """Analyze a single Python file."""
        try:
            content = py_file.read_text()
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError:
            return  # Skip files with syntax errors

        rel_path = str(py_file.relative_to(self.root_dir))

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[alias.name].append(rel_path)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module
                    for alias in node.names:
                        full_name = f"{module}.{alias.name}"
                        self.imports[full_name].append(rel_path)
                        self.imports[module].append(rel_path)

            # Extract function and class definitions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.definitions[node.name].append(rel_path)

    def find_orphaned_imports(self) -> List[Dict]:
        """Find imports that don't correspond to existing modules."""
        print("\n:left-pointing_magnifying_glass: Finding orphaned imports...")

        orphaned = []

        # Get all module paths
        module_names = set()
        for py_file in self.python_files:
            rel_path = py_file.relative_to(self.root_dir)
            # Convert file path to module name
            module = str(rel_path).replace("/", ".").replace(".py", "")
            module_names.add(module)

            # Add parent packages
            parts = module.split(".")
            for i in range(1, len(parts)):
                module_names.add(".".join(parts[:i]))

        # Check each import
        for imported_module, importing_files in self.imports.items():
            # Skip standard library and third-party
            if not imported_module.startswith("dsa110_contimg"):
                continue

            # Check if module exists
            if imported_module not in module_names:
                orphaned.append(
                    {
                        "module": imported_module,
                        "imported_by": importing_files[:5],  # Limit to first 5
                        "count": len(importing_files),
                    }
                )

        return orphaned

    def generate_migration_map(self, old_new_mapping: Dict[str, str]) -> Dict:
        """
        Generate a migration map showing what needs to be updated.

        Args:
            old_new_mapping: Dict of old_module -> new_module paths
        """
        print("\n:clipboard: Generating migration checklist...")

        migration_tasks = []

        for old_path, new_path in old_new_mapping.items():
            if old_path in self.imports:
                files_to_update = self.imports[old_path]
                migration_tasks.append(
                    {
                        "old": old_path,
                        "new": new_path,
                        "files_to_update": files_to_update,
                        "count": len(files_to_update),
                        "status": "pending",
                    }
                )

        return {"total_tasks": len(migration_tasks), "tasks": migration_tasks}

    def find_test_coverage_gaps(self) -> List[Dict]:
        """Identify modules without corresponding test files."""
        print("\n:test_tube: Checking test coverage...")

        # Find all test files
        test_files = set()
        for py_file in self.python_files:
            if "test" in str(py_file):
                test_files.add(py_file)

        # Find modules without tests
        untested = []

        for py_file in self.python_files:
            # Skip test files themselves
            if "test" in str(py_file):
                continue

            # Skip __init__ files
            if py_file.name == "__init__.py":
                continue

            # Check if corresponding test exists
            rel_path = py_file.relative_to(self.root_dir)

            # Look for test_<module>.py or <module>_test.py
            possible_test_names = [
                f"test_{py_file.stem}.py",
                f"{py_file.stem}_test.py",
            ]

            has_test = False
            for test_file in test_files:
                if test_file.name in possible_test_names:
                    has_test = True
                    break

            if not has_test:
                # Check if it's a substantial file (more than just imports)
                try:
                    content = py_file.read_text()
                    tree = ast.parse(content)

                    # Count functions and classes
                    func_count = sum(
                        1
                        for node in ast.walk(tree)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    class_count = sum(
                        1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
                    )

                    if func_count > 0 or class_count > 0:
                        untested.append(
                            {
                                "file": str(rel_path),
                                "functions": func_count,
                                "classes": class_count,
                                "priority": "high" if (func_count + class_count) > 5 else "medium",
                            }
                        )
                except:
                    pass

        return untested

    def generate_report(self, output_file: str = None):
        """Generate comprehensive refactoring report."""
        print("\n" + "=" * 70)
        print(":bar_chart: REFACTORING IMPACT REPORT")
        print("=" * 70)

        # Find orphaned imports
        orphaned = self.find_orphaned_imports()
        print(f"\n:large_red_circle: Orphaned Imports: {len(orphaned)}")
        for item in orphaned[:10]:
            print(f"   • {item['module']} (used in {item['count']} files)")
            if item["count"] <= 3:
                for f in item["imported_by"]:
                    print(f"     - {f}")

        # Check test coverage
        untested = self.find_test_coverage_gaps()
        print(f"\n:test_tube: Files Without Tests: {len(untested)}")
        high_priority = [u for u in untested if u["priority"] == "high"]
        print(f"   High Priority: {len(high_priority)}")
        for item in high_priority[:10]:
            print(f"   • {item['file']} ({item['functions']} funcs, {item['classes']} classes)")

        # Save detailed report
        if output_file:
            report_data = {
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "total_files": len(self.python_files),
                "orphaned_imports": orphaned,
                "untested_modules": untested,
                "import_graph": {
                    k: v for k, v in self.imports.items() if k.startswith("dsa110_contimg")
                },
            }

            output_path = Path(output_file)
            output_path.write_text(json.dumps(report_data, indent=2))
            print(f"\n:floppy_disk: Detailed report saved to: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze refactoring impact")
    parser.add_argument(
        "--root",
        default="/data/dsa110-contimg/backend/src/dsa110_contimg",
        help="Root directory of the project",
    )
    parser.add_argument(
        "--output", default="refactor_analysis.json", help="Output file for detailed report"
    )

    args = parser.parse_args()

    analyzer = RefactorAnalyzer(args.root)
    analyzer.scan()
    analyzer.generate_report(args.output)

    print("\n" + "=" * 70)
    print(":white_heavy_check_mark: Analysis complete!")
    print("\nNext steps:")
    print("1. Review orphaned imports and update them")
    print("2. Add tests for high-priority untested modules")
    print("3. Update documentation to reflect new structure")
    print("=" * 70)


if __name__ == "__main__":
    main()
