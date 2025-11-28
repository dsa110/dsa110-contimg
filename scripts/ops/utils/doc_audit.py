#!/opt/miniforge/envs/casa6/bin/python
"""
Doc audit utility:
 - extracts API endpoint paths from Markdown and checks they exist in FastAPI routes
 - finds repo-relative file path references and verifies existence
 - lists suspect references per file for manual review

Usage:
  python scripts/doc_audit.py [globs...]
Defaults:
  docs/index.md docs/how-to/**/*.md docs/reference/**/*.md
"""

import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

# Compute repository root (this script lives at scripts/ops/utils/)
ROOT = Path(__file__).resolve().parents[3]


def gather_routes() -> Set[str]:
    """Collect endpoints with best-effort prefix resolution for included routers."""
    dec_pat = re.compile(r"@(app|router)\.(get|post|put|delete|websocket)\(\s*['\"]([^'\"]+)['\"]")
    include_alias_pat = re.compile(
        r"app\.include_router\((?P<alias>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?:,\s*prefix=\"(?P<prefix>[^\"]+)\")?"
    )
    include_module_pat = re.compile(
        r"app\.include_router\((?P<mod>[a-zA-Z_][a-zA-Z0-9_]*)_router_module\.router\s*,\s*prefix=\"(?P<prefix>[^\"]+)\"\)"
    )
    import_alias_pat = re.compile(
        r"from\s+dsa110_contimg\.api\.routers\.(?P<mod>[a-zA-Z_][a-zA-Z0-9_]*)\s+import\s+router\s+as\s+(?P<alias>[a-zA-Z_][a-zA-Z0-9_]*)"
    )

    routes: Set[str] = set()

    # Locate API source trees - check ALL candidates (backend + legacy.backend)
    api_root_candidates = [
        ROOT / "backend" / "src" / "dsa110_contimg" / "api",
        ROOT / "legacy.backend" / "src" / "dsa110_contimg" / "api",
        ROOT / "src" / "dsa110_contimg" / "api",
    ]

    # Helper to add decorated routes from a file, with optional prefix
    def add_from_file(path: Path, prefix: str = ""):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return
        for m in dec_pat.finditer(text):
            target = m.group(1)  # app or router
            p = m.group(3)
            if not p.startswith("/"):
                continue
            # Only apply prefix to routes declared on a prefixed router
            if prefix and target == "router":
                full = f"{prefix}{p}"
            else:
                full = p
            routes.add(full)

    # Process ALL existing API roots (not just first match)
    for api_root in api_root_candidates:
        if not api_root.exists():
            continue

        routes_py = api_root / "routes.py"
        # Map router alias -> module name
        alias_to_mod: Dict[str, str] = {}
        # Map module/alias -> prefix as included
        alias_prefix: Dict[str, str] = {}
        if routes_py.exists():
            s = routes_py.read_text(encoding="utf-8")
            for m in import_alias_pat.finditer(s):
                alias_to_mod[m.group("alias")] = m.group("mod")
            for m in include_alias_pat.finditer(s):
                alias = m.group("alias")
                prefix = m.group("prefix") or ""
                alias_prefix[alias] = prefix
            for m in include_module_pat.finditer(s):
                mod = m.group("mod")
                alias_prefix[mod] = m.group("prefix")

        # Include subrouter modules with discovered prefixes
        routers_dir = api_root / "routers"
        if routers_dir.exists():
            for f in routers_dir.glob("*.py"):
                mod = f.stem
                prefix = None
                # Prefer explicit module mapping
                if mod in alias_prefix:
                    prefix = alias_prefix[mod]
                else:
                    # Try via alias mapping
                    for alias, a_mod in alias_to_mod.items():
                        if a_mod == mod and alias in alias_prefix:
                            prefix = alias_prefix[alias]
                            break
                add_from_file(f, prefix or "/api")

        # Add routes declared in routes.py 'router' (no prefix)
        # For routes.py, apply APIRouter prefix (/api) to router-decorated endpoints
        add_from_file(routes_py, "/api")

    return routes


def extract_api_paths(md_text: str) -> Set[str]:
    # Capture /api/... and also bare paths like /status if used
    paths = set(re.findall(r"(?<![A-Za-z0-9_])(\/[A-Za-z0-9_\-\/\{\}:\.]+)", md_text))
    # Only care about endpoints that look like they belong to our API
    return {p for p in paths if p.startswith("/api/") or p in ("/status", "/health")}


def extract_file_paths(md_text: str) -> Set[str]:
    # Look for inline code blocks with repo paths like src/... or scripts/... or ops/...
    cands = set(re.findall(r"`((?:src|scripts|ops|frontend|docs)/[^`\s]+)`", md_text))
    return cands


def is_placeholder_or_glob(path: str) -> bool:
    """Check if a path is a glob pattern or placeholder, not a literal file reference."""
    # Glob patterns
    if "*" in path or "?" in path:
        return True
    # Placeholder patterns like <ComponentName> or ...
    if "<" in path and ">" in path:
        return True
    if "..." in path:
        return True
    # Template placeholders
    if "{" in path and "}" in path:
        return True
    return False


def find_md_files(patterns: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    if not patterns:
        patterns = [
            "docs/index.md",
            "docs/how-to/**/*.md",
            "docs/reference/**/*.md",
        ]
    for pat in patterns:
        files.extend(ROOT.glob(pat))
    # De-dup and keep only files
    out: List[Path] = []
    seen = set()
    for f in files:
        if f.is_file() and f.suffix == ".md" and f not in seen:
            out.append(f)
            seen.add(f)
    return out


def main(argv: List[str]) -> int:
    routes = gather_routes()
    files = find_md_files(argv[1:])
    missing: List[Tuple[str, str, str]] = []
    bad_files: List[Tuple[str, str]] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        apis = extract_api_paths(text)
        for ep in sorted(apis):
            ep_no_host = re.sub(r"https?://[^/]+", "", ep)
            probe = ep_no_host
            probe2 = ep_no_host[4:] if ep_no_host.startswith("/api/") else ep_no_host
            # Heuristic: ignore example endpoints with literal IDs/timestamps
            if re.search(r"\d{4}-\d{2}-\d{2}T", ep_no_host):
                continue
            if probe not in routes and probe2 not in routes:
                missing.append((str(f.relative_to(ROOT)), ep, "not found in app routes"))
        paths = extract_file_paths(text)
        for p in sorted(paths):
            # Skip glob patterns and placeholder paths
            if is_placeholder_or_glob(p):
                continue
            full = ROOT / p
            if not full.exists():
                bad_files.append((str(f.relative_to(ROOT)), p))
    # Print report
    # Auto-generate verified endpoint sections
    generate_verified_docs(routes)

    if missing:
        print("Missing API endpoints referenced in docs:")
        for doc, ep, reason in missing:
            print(f"- {doc}: {ep} ({reason})")
    else:
        print("No missing API endpoints found in scanned docs.")
    if bad_files:
        print("\nNon-existent file paths referenced in docs:")
        for doc, p in bad_files:
            print(f"- {doc}: `{p}`")
    else:
        print("\nNo bad file path references found.")
    print(f"\nScanned {len(files)} docs. Routes discovered: {len(routes)}")
    # Fail in CI if mismatches found
    return 1 if missing else 0


def generate_verified_docs(routes: Set[str]) -> None:
    """Write verified endpoint sections into reference docs."""
    # Build groups by top-level key (after /api)
    api_routes = sorted(r for r in routes if r.startswith("/api/"))
    groups: Dict[str, List[str]] = {}
    for r in api_routes:
        parts = r.split("/")
        key = parts[2] if len(parts) > 2 else "api"
        groups.setdefault(key, []).append(r)

    # docs/reference/api-endpoints.md: overwrite with verified list
    out_api = ROOT / "docs/reference/api-endpoints.md"
    lines: List[str] = ["# Reference: API (Verified)\n\n"]
    for key in sorted(groups.keys()):
        lines.append(f"## {key}\n")
        for ep in sorted(groups[key]):
            lines.append(f"- `{ep}`\n")
        lines.append("\n")
    out_api.write_text("".join(lines), encoding="utf-8")

    # docs/reference/dashboard_backend_api.md: insert/update a verified section
    dash = ROOT / "docs/reference/dashboard_backend_api.md"
    if dash.exists():
        content = dash.read_text(encoding="utf-8")
        start = "<!-- BEGIN: VERIFIED-ENDPOINTS -->"
        end = "<!-- END: VERIFIED-ENDPOINTS -->"
        block_lines = [
            start,
            "\n## Verified Endpoints (auto-generated)\n\n",
        ]
        for key in sorted(groups.keys()):
            block_lines.append(f"### {key}\n")
            for ep in sorted(groups[key]):
                block_lines.append(f"- `{ep}`\n")
            block_lines.append("\n")
        block_lines.append(end)
        block = "".join(block_lines)
        if start in content and end in content:
            new = re.sub(f"{start}.*?{end}", block, content, flags=re.S)
        else:
            # Insert near top after title
            new = content + "\n\n" + block
        dash.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
