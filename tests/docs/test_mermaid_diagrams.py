"""
Mermaid diagram visual checks for MkDocs pages.

Implements the strategy described in docs/testing/MERMAID_DIAGRAM_TESTING_STRATEGY.md.
Parses mkdocs.yml nav, serves the site (handled by CI workflow), and visits each
page with Playwright to detect Mermaid rendering errors.
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

import pytest
import yaml
from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("DOCS_BASE_URL", "http://127.0.0.1:8001")
REPO_ROOT = Path(__file__).resolve().parents[2]
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"


def _flatten_nav(nav: List[Union[Dict[str, Any], str]]) -> List[str]:
    paths: List[str] = []
    for item in nav:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict):
            for _title, value in item.items():
                if isinstance(value, str):
                    paths.append(value)
                elif isinstance(value, list):
                    paths.extend(_flatten_nav(value))
                elif isinstance(value, dict):
                    # Rare: nested dict
                    paths.extend(_flatten_nav([value]))
    return paths


def _mkdocs_paths() -> List[str]:
    with MKDOCS_YML.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    nav = cfg.get("nav", [])
    raw_paths = _flatten_nav(nav)
    # Keep only markdown pages under docs/
    md_paths = [p for p in raw_paths if isinstance(p, str) and p.endswith(".md")]
    return md_paths


def _to_url(md_path: str) -> str:
    # Normalize docs-relative path
    if md_path.startswith("docs/"):
        rel = md_path[len("docs/") :]
    else:
        rel = md_path

    # Index handling
    if rel == "index.md":
        return f"{BASE_URL}/"
    if rel.endswith("/index.md"):
        return f"{BASE_URL}/" + rel[: -len("index.md")]

    # Standard page → directory URL style
    rel_no_ext = rel[:-3]
    return f"{BASE_URL}/" + rel_no_ext + "/"


def _pages_to_check() -> List[str]:
    md_paths = _mkdocs_paths()
    # De-duplicate while preserving order
    seen = set()
    pages: List[str] = []
    for p in md_paths:
        if p not in seen:
            seen.add(p)
            pages.append(p)
    return pages


@pytest.mark.parametrize("md_path", _pages_to_check())
def test_mermaid_diagrams_render_without_errors(md_path: str) -> None:
    url = _to_url(md_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="load", timeout=30000)

        # Allow time for Mermaid (CDN) and our init script to run
        page.wait_for_timeout(3000)

        # Fail if Mermaid shows its syntax error indicators
        page_text = page.content()
        assert "Syntax error in text" not in page_text, f"Mermaid syntax error on {url}"

        # If there are Mermaid containers, ensure at least some rendered SVGs exist
        mermaid_count = page.locator(".mermaid").count()
        if mermaid_count > 0:
            # Give a little more time for render
            page.wait_for_timeout(2000)
            svgs = page.locator(".mermaid svg").count()
            assert svgs > 0, f"Mermaid present but no rendered SVGs on {url}"

        browser.close()
