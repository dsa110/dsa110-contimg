#!/opt/miniforge/envs/casa6/bin/python
"""Generate mkdocs.yml with metadata from pyproject.toml.

This script reads package metadata from pyproject.toml and updates
mkdocs.yml to use that metadata, ensuring consistency.
"""

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ImportError:
        print("ERROR: Need tomllib (Python 3.11+) or tomli package")
        sys.exit(1)

import yaml


def load_pyproject_metadata(pyproject_path: Path) -> dict:
    """Load metadata from pyproject.toml."""
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    return {
        "name": project.get("name", "dsa110-contimg"),
        "version": project.get("version", "0.1.0"),
        "description": project.get("description", ""),
        "authors": project.get("authors", []),
        "license": project.get("license", {}),
    }


def update_mkdocs_config(mkdocs_path: Path, metadata: dict) -> None:
    """Update mkdocs.yml with package metadata by editing the file directly."""
    # Read the file
    with open(mkdocs_path, "r") as f:
        lines = f.readlines()

    # Update site_name
    site_name = metadata["description"] or metadata["name"].replace("-", " ").title()
    for i, line in enumerate(lines):
        if line.startswith("site_name:"):
            lines[i] = f"site_name: {site_name}\n"
            break

    # Check if extra section exists
    extra_start = None
    for i, line in enumerate(lines):
        if line.strip() == "extra:":
            extra_start = i
            break

    # Add or update extra section
    extra_lines = [
        "extra:\n",
        f"  version: {metadata['version']}\n",
        f"  package_name: {metadata['name']}\n",
        f"  description: {metadata['description']}\n",
    ]

    if metadata.get("license"):
        if isinstance(metadata["license"], dict):
            license_text = metadata["license"].get("text", "")
        else:
            license_text = str(metadata["license"])
        if license_text:
            extra_lines.append(f"  license: {license_text}\n")

    if metadata.get("authors"):
        authors = [a.get("name", str(a)) for a in metadata["authors"] if isinstance(a, dict)]
        if authors:
            extra_lines.append(f"  authors: {', '.join(authors)}\n")

    if extra_start is not None:
        # Replace existing extra section
        # Find where extra section ends (next top-level key)
        extra_end = extra_start + 1
        for i in range(extra_start + 1, len(lines)):
            line_stripped = lines[i].strip()
            # Stop at next top-level key (no leading space) or empty line followed by top-level key
            if line_stripped and not lines[i].startswith(" ") and not line_stripped.startswith("#"):
                extra_end = i
                break
            # Also stop if we hit a blank line and the next non-blank is top-level
            if not line_stripped:
                # Check next non-blank line
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():
                        if not lines[j].startswith(" ") and not lines[j].strip().startswith("#"):
                            extra_end = i
                            break
                        break
                if extra_end < len(lines):
                    break

        # Replace the extra section
        lines[extra_start:extra_end] = extra_lines
    else:
        # Add extra section before nav
        nav_index = None
        for i, line in enumerate(lines):
            if line.strip() == "nav:":
                nav_index = i
                break

        if nav_index is not None:
            lines.insert(nav_index, "\n")
            for extra_line in reversed(extra_lines):
                lines.insert(nav_index, extra_line)
        else:
            # Append at end
            lines.extend(["\n"] + extra_lines)

    # Write back
    with open(mkdocs_path, "w") as f:
        f.writelines(lines)


def update_markdown_files(repo_root: Path, metadata: dict) -> None:
    """Update markdown files with actual package metadata values."""
    # Files that reference package metadata
    files_to_update = [
        repo_root / "docs" / "index.md",
        repo_root / "docs" / "how-to" / "package_installation.md",
    ]

    package_name = metadata["name"]
    version = metadata["version"]
    description = metadata.get("description", "")

    for file_path in files_to_update:
        if not file_path.exists():
            continue

        with open(file_path, "r") as f:
            content = f.read()

        # Replace template variables with actual values
        original_content = content
        content = content.replace("{{ config.extra.package_name }}", package_name)
        content = content.replace("{{ config.extra.version }}", version)
        content = content.replace("{% if config.extra.description %}", "")
        content = content.replace("{{ config.extra.description }}", description)
        content = content.replace("{% endif %}", "")

        # Clean up any remaining template artifacts
        content = content.replace("{{ config.extra.package_name }}", package_name)
        content = content.replace("{{ config.extra.version }}", version)

        # Only write if content changed
        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            print(f"  Updated {file_path.name} with package metadata")


def main():
    """Main function."""
    repo_root = Path(__file__).parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    mkdocs_path = repo_root / "mkdocs.yml"

    if not pyproject_path.exists():
        print(f"ERROR: {pyproject_path} not found")
        sys.exit(1)

    if not mkdocs_path.exists():
        print(f"ERROR: {mkdocs_path} not found")
        sys.exit(1)

    # Load metadata
    metadata = load_pyproject_metadata(pyproject_path)

    # Update mkdocs config
    update_mkdocs_config(mkdocs_path, metadata)

    # Update markdown files with actual values (since MkDocs doesn't process Jinja2 in markdown)
    update_markdown_files(repo_root, metadata)

    print(f":check: Updated {mkdocs_path} with metadata from {pyproject_path}")
    print(f"  Site name: {metadata['description'] or metadata['name'].replace('-', ' ').title()}")
    print(f"  Version: {metadata['version']}")


if __name__ == "__main__":
    main()
