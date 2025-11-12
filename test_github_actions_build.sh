#!/bin/bash
# Simulate GitHub Actions build process

set -euo pipefail

echo "=== Simulating GitHub Actions Build ==="
echo "Python version:"
python3 --version

echo ""
echo "=== Upgrading pip ==="
python3 -m pip install --upgrade pip

echo ""
echo "=== Installing dependencies ==="
python3 -m pip install -r docs/requirements.txt

echo ""
echo "=== Building MkDocs ==="
python3 -m mkdocs build --strict

echo ""
echo "=== Build successful! ==="

