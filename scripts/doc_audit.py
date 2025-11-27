#!/usr/bin/env python3
"""
Wrapper to run the documentation audit from its canonical location.

Keeps .husky/pre-commit working regardless of where the audit script lives.
"""

from pathlib import Path
import subprocess
import sys


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent
    target = root / "ops" / "utils" / "doc_audit.py"

    if not target.is_file():
        print(f"Error: audit script not found at {target}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(target), *argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
