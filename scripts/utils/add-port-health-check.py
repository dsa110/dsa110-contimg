#!/opt/miniforge/envs/casa6/bin/python
"""Helper to add port health check to API routes."""

import sys
from pathlib import Path

api_routes = Path("src/dsa110_contimg/api/routes.py")

if not api_routes.exists():
    print("API routes file not found")
    sys.exit(1)

# Check if health check already exists
content = api_routes.read_text()
if "/health/ports" in content:
    print("Port health check already exists")
    sys.exit(0)

# Add health check endpoint (would need manual integration)
print("Port health check helper created")
print("Manually add /health/ports endpoint to routes.py")
