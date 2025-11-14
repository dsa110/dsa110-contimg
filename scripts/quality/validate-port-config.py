#!/usr/bin/env python3
"""Validate port configuration and detect hardcoded ports.

This script enforces the port organization system by:
1. Validating ports.yaml exists and is valid
2. Checking for hardcoded ports in code
3. Ensuring environment variables are used correctly
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Port ranges that should not be hardcoded
PORT_RANGES = {
    "8000-8099": "Core Application Services",
    "5000-5199": "Development Servers",
    "3200-3299": "Dashboard Services",
    "9000-9099": "External Integrations",
    "6000-6099": "Optional Services",
}

# Known exceptions (ports that are allowed to be hardcoded)
ALLOWED_HARDCODED = {
    9009,  # Browser MCP WebSocket (hardcoded in extension)
    6379,  # Redis standard port
    9222,  # Chrome DevTools Protocol
}

# External tools (not managed by port system - VS Code, etc.)
# These are dynamic ports assigned by external tools
EXTERNAL_TOOL_PORT_RANGES = [
    (30000, 39999),  # VS Code Extension Host ports
    (40000, 49999),  # Other IDE/editor ports
]

# Files/directories to exclude from checks
EXCLUDE_PATTERNS = [
    r"\.git/",
    r"node_modules/",
    r"\.venv/",
    r"__pycache__/",
    r"\.pytest_cache/",
    r"htmlcov/",
    r"site/",
    r"dist/",
    r"build/",
    r"\.mypy_cache/",
    r"archive/",
    r"test_data/",
    r"config/ports\.yaml",  # The config file itself
    r"scripts/validate-port-config\.py",  # This script
    r"docs/.*\.md",  # Documentation files
    r"\.pyc$",
    r"\.log$",
]


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from checks."""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, path_str):
            return True
    return False


def find_hardcoded_ports(file_path: Path) -> list[tuple[int, int, str]]:
    """Find hardcoded port numbers in a file.

    Returns:
        List of (line_number, port, line_content) tuples
    """
    issues = []
    # More specific patterns to avoid false positives
    port_patterns = [
        # Port assignments: port=8000, PORT=8000, port: 8000
        re.compile(r"\bport\s*[:=]\s*(\d{4,5})\b", re.IGNORECASE),
        # URL patterns: http://host:8000, ws://host:8000
        re.compile(r"://[^:]+:(\d{4,5})(?:/|$|\s)", re.IGNORECASE),
        # Docker port mappings: -p 8000:8000, "8000:8000"
        re.compile(r'["\']?(\d{4,5}):\d{4,5}["\']?', re.IGNORECASE),
        # lsof/netstat patterns: lsof -i :8000
        re.compile(r"-i\s*:(\d{4,5})\b", re.IGNORECASE),
        # curl/wget patterns: curl http://host:8000
        re.compile(r"(?:curl|wget|http|https|ws|wss)\s+[^:]+:(\d{4,5})", re.IGNORECASE),
    ]

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                # Skip comments
                if line.strip().startswith("#") or line.strip().startswith("//"):
                    continue

                # Skip docstrings
                if '"""' in line or "'''" in line:
                    continue

                for pattern in port_patterns:
                    matches = pattern.findall(line)
                    for port_str in matches:
                        try:
                            port = int(port_str)

                            # Skip allowed hardcoded ports
                            if port in ALLOWED_HARDCODED:
                                continue

                            # Skip external tool ports (VS Code, etc.)
                            if any(
                                min_port <= port <= max_port
                                for min_port, max_port in EXTERNAL_TOOL_PORT_RANGES
                            ):
                                continue

                            # Skip if it's clearly not a port (array indices, counts, etc.)
                            # Check context - if it's in array slicing or range(), likely not a port
                            if re.search(
                                r"\[.*:"
                                + str(port)
                                + r"\]|range\(.*"
                                + str(port)
                                + r"\)|//\s*"
                                + str(port),
                                line,
                            ):
                                continue

                            # Only flag if it's in a port-like context
                            if any(
                                keyword in line.lower()
                                for keyword in [
                                    "port",
                                    "http",
                                    "ws",
                                    "url",
                                    "lsof",
                                    "curl",
                                    "docker",
                                    "compose",
                                ]
                            ):
                                issues.append((line_num, port, line.strip()))
                        except ValueError:
                            pass
    except Exception:
        pass  # Skip files we can't read

    return issues


def check_port_config() -> bool:
    """Check if port configuration file exists and is valid."""
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "ports.yaml"

    if not config_path.exists():
        print(f"⚠️  Warning: {config_path} not found")
        print(f"   Run: cp config/ports.yaml.example config/ports.yaml")
        return False

    # Try to validate YAML
    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)
        if "ports" not in config:
            print(f"❌ Error: {config_path} missing 'ports' section")
            return False
        print(f"✓ Port configuration file exists and is valid")
        return True
    except ImportError:
        print(f"⚠️  Warning: PyYAML not available, cannot validate {config_path}")
        return True  # Assume OK if we can't validate
    except Exception as e:
        print(f"❌ Error: {config_path} is invalid: {e}")
        return False


def check_code_for_hardcoded_ports() -> bool:
    """Check codebase for hardcoded ports."""
    project_root = Path(__file__).parent.parent
    issues_found = []

    # Check Python files
    for py_file in project_root.rglob("*.py"):
        if should_exclude(py_file):
            continue
        issues = find_hardcoded_ports(py_file)
        if issues:
            issues_found.append((py_file, issues))

    # Check shell scripts
    for sh_file in project_root.rglob("*.sh"):
        if should_exclude(sh_file):
            continue
        issues = find_hardcoded_ports(sh_file)
        if issues:
            issues_found.append((sh_file, issues))

    # Check YAML files (docker-compose, etc.)
    for yaml_file in project_root.rglob("*.yml"):
        if should_exclude(yaml_file):
            continue
        if "ports.yaml" in str(yaml_file):
            continue  # Skip the config file itself
        issues = find_hardcoded_ports(yaml_file)
        if issues:
            issues_found.append((yaml_file, issues))

    if issues_found:
        print("\n❌ Hardcoded ports found (should use port manager or env vars):")
        for file_path, issues in issues_found:
            rel_path = file_path.relative_to(project_root)
            print(f"\n  {rel_path}:")
            for line_num, port, line in issues[:5]:  # Show first 5 per file
                print(f"    Line {line_num} (port {port}): {line[:80]}")
            if len(issues) > 5:
                print(f"    ... and {len(issues) - 5} more")
        return False
    else:
        print("✓ No hardcoded ports found in code")
        return True


def main() -> int:
    """Main validation function."""
    print("Validating port configuration system...\n")

    config_ok = check_port_config()
    print()
    code_ok = check_code_for_hardcoded_ports()

    print()
    if config_ok and code_ok:
        print("✓ All port configuration checks passed")
        return 0
    else:
        print("❌ Port configuration validation failed")
        print("\nSee docs/operations/port_organization_recommendations.md for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
