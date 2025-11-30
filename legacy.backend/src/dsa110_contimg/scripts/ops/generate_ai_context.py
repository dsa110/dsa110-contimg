#!/usr/bin/env python3
"""
AI Context Generator

Creates concise context files that AI agents can consume to understand:
- Project structure
- Recent changes
- Known issues
- Key conventions

This helps AI agents maintain "the thread" when working on large codebases.
"""

import ast
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


class ContextGenerator:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.context = {
            "generated_at": datetime.now().isoformat(),
            "project_root": str(root_dir),
        }

    def generate_structure_overview(self) -> Dict:
        """Generate a concise overview of project structure."""
        print(":open_file_folder: Analyzing project structure...")

        structure = {"main_packages": [], "key_directories": {}, "entry_points": []}

        # Find main packages (directories with __init__.py)
        for item in self.root_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                structure["main_packages"].append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(self.root_dir)),
                        "submodules": len([x for x in item.iterdir() if x.suffix == ".py"]),
                    }
                )

        # Identify key directories
        key_dirs = ["tests", "scripts", "docs", "examples", "config"]
        for dir_name in key_dirs:
            dir_path = self.root_dir / dir_name
            if dir_path.exists():
                structure["key_directories"][dir_name] = {
                    "path": str(dir_path.relative_to(self.root_dir)),
                    "file_count": len(list(dir_path.rglob("*.py"))),
                }

        # Find entry points (scripts with __main__ or CLI)
        for py_file in self.root_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                if (
                    "if __name__ == '__main__'" in content
                    or "click.command" in content
                    or "argparse" in content
                ):
                    structure["entry_points"].append(str(py_file.relative_to(self.root_dir)))
            except:
                pass

        return structure

    def get_recent_changes(self, days: int = 7) -> List[Dict]:
        """Get recent git commits to understand what changed."""
        print(f":scroll: Fetching recent changes (last {days} days)...")

        try:
            # Get commits from last N days
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={since_date}",
                    "--pretty=format:%h|%an|%ar|%s",
                    "--no-merges",
                ],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        }
                    )

            return commits[:20]  # Limit to most recent 20

        except Exception as e:
            print(f"   :warning:  Could not fetch git history: {e}")
            return []

    def identify_key_modules(self) -> List[Dict]:
        """Identify the most important modules based on imports."""
        print(":key: Identifying key modules...")

        import_counts = {}

        for py_file in self.root_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("dsa110_contimg"):
                            import_counts[node.module] = import_counts.get(node.module, 0) + 1
            except:
                pass

        # Sort by frequency
        sorted_modules = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            {"module": mod, "import_count": count} for mod, count in sorted_modules[:15]  # Top 15
        ]

    def extract_conventions(self) -> Dict:
        """Extract coding conventions from the codebase."""
        print(":triangular_ruler: Extracting conventions...")

        conventions = {"naming": {}, "imports": [], "common_patterns": []}

        # Look for naming conventions in existing code
        class_names = []
        function_names = []

        for py_file in list(self.root_dir.rglob("*.py"))[:50]:  # Sample 50 files
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_names.append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        function_names.append(node.name)
            except:
                pass

        # Analyze naming patterns
        if class_names:
            conventions["naming"]["classes"] = (
                "PascalCase" if any(c[0].isupper() for c in class_names) else "unknown"
            )

        if function_names:
            conventions["naming"]["functions"] = (
                "snake_case" if any("_" in f for f in function_names) else "unknown"
            )

        return conventions

    def generate_ai_context_file(self, output_file: str = ".ai-context.json"):
        """Generate the complete context file."""
        print("\n:robot_face: Generating AI context file...")

        self.context["structure"] = self.generate_structure_overview()
        self.context["recent_changes"] = self.get_recent_changes(days=14)
        self.context["key_modules"] = self.identify_key_modules()
        self.context["conventions"] = self.extract_conventions()

        # Add usage instructions for AI
        self.context["ai_instructions"] = {
            "purpose": "This file helps AI agents understand the codebase structure and recent changes",
            "usage": [
                "Review structure.main_packages to understand the project organization",
                "Check recent_changes to see what was modified recently",
                "Consult key_modules to understand core dependencies",
                "Follow conventions when generating new code",
            ],
            "update_frequency": "Run scripts/generate_ai_context.py after major refactoring or weekly",
        }

        # Save to file
        output_path = self.root_dir / output_file
        output_path.write_text(json.dumps(self.context, indent=2))

        print(f"\n:white_heavy_check_mark: Context file saved to: {output_path}")
        return output_path

    def generate_markdown_summary(self):
        """Generate a human-readable markdown summary."""
        print("\n:memo: Generating markdown summary...")

        lines = [
            "# AI Context Summary",
            f"\n*Generated: {self.context['generated_at']}*",
            "\n## :open_file_folder: Project Structure",
        ]

        if "structure" in self.context:
            lines.append("\n### Main Packages")
            for pkg in self.context["structure"]["main_packages"]:
                lines.append(f"- **{pkg['name']}** ({pkg['submodules']} modules)")

        if "key_modules" in self.context:
            lines.append("\n## :key: Most Imported Modules")
            for mod in self.context["key_modules"][:10]:
                lines.append(f"- `{mod['module']}` ({mod['import_count']} imports)")

        if "recent_changes" in self.context and self.context["recent_changes"]:
            lines.append("\n## :scroll: Recent Changes (Last 14 Days)")
            for commit in self.context["recent_changes"][:10]:
                lines.append(f"- `{commit['hash']}` {commit['message']} *({commit['date']})*")

        markdown = "\n".join(lines)

        output_path = self.root_dir / ".ai-context.md"
        output_path.write_text(markdown)

        print(f":white_heavy_check_mark: Markdown summary saved to: {output_path}")
        return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate AI context files for better agent understanding"
    )
    parser.add_argument(
        "--root", default="/data/dsa110-contimg/backend/src", help="Root directory of the project"
    )
    parser.add_argument("--output", default=".ai-context.json", help="Output file name")

    args = parser.parse_args()

    print("=" * 70)
    print(":robot_face: AI Context Generator")
    print("=" * 70)

    generator = ContextGenerator(args.root)
    generator.generate_ai_context_file(args.output)
    generator.generate_markdown_summary()

    print("\n" + "=" * 70)
    print(":white_heavy_check_mark: Context generation complete!")
    print("\n:electric_light_bulb: Usage Tips:")
    print("1. Share .ai-context.json with AI agents at the start of conversations")
    print("2. Reference .ai-context.md when asking AI to understand recent changes")
    print("3. Re-run this script after major refactoring or weekly")
    print("4. Commit .ai-context.md to git for team visibility")
    print("=" * 70)


if __name__ == "__main__":
    main()
