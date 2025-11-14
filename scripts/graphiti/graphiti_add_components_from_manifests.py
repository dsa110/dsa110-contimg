#!/usr/bin/env python3
"""
Add SoftwareComponent nodes and DEPENDS_ON edges by scanning dependency manifests
in a repository (requirements*.txt, package.json) without running a full importer.

Usage:
  uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
    python /data/dsa110-contimg/scripts/graphiti_add_components_from_manifests.py \
    --root /data/dsa110-contimg --group-id dsa110-contimg --project-name dsa110-contimg

Notes:
  - Uses Graphiti's driver directly; no LLM/embeddings required.
  - Creates/labels a project SoftwareComponent and adds DEPENDS_ON edges to discovered deps.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from graphiti_core import Graphiti


def parse_requirements(path: Path) -> list[str]:
    deps: list[str] = []
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return deps
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Strip hashes/extras/markers
        s = s.split(" ")[0]
        s = s.split(";")[0]
        s = s.split("[", 1)[0]
        for sep in ["==", ">=", "<=", "~=", ">", "<", "!=" ]:
            if sep in s:
                s = s.split(sep, 1)[0]
                break
        name = s.strip().lower()
        if name:
            deps.append(name)
    return deps


def parse_package_json(path: Path) -> list[str]:
    deps: list[str] = []
    try:
        data = json.loads(path.read_text(errors="ignore"))
    except Exception:
        return deps
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        d = data.get(key)
        if isinstance(d, dict):
            deps.extend([k.strip().lower() for k in d.keys()])
    return deps


def scan(root: Path) -> dict[str, set[str]]:
    eco_to_deps: dict[str, set[str]] = {"pypi": set(), "npm": set()}
    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    for dirpath, dirnames, filenames in os.walk(root):
        # prune
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith('.')]
        dpath = Path(dirpath)
        for fn in filenames:
            if fn.startswith('.'):
                continue
            fpath = dpath / fn
            name_l = fn.lower()
            try:
                if name_l == 'package.json':
                    for dep in parse_package_json(fpath):
                        eco_to_deps["npm"].add(dep)
                elif name_l.startswith('requirements') and name_l.endswith('.txt'):
                    for dep in parse_requirements(fpath):
                        eco_to_deps["pypi"].add(dep)
            except Exception:
                continue
    return eco_to_deps


import asyncio


async def main_async() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--group-id", required=True)
    ap.add_argument("--project-name", default="dsa110-contimg")
    ap.add_argument("--env", default="/home/ubuntu/proj/mcps/graphiti/mcp_server/.env")
    args = ap.parse_args()

    load_dotenv(args.env)

    deps_by_eco = scan(args.root)
    rows = []
    for eco, deps in deps_by_eco.items():
        for dep in sorted(deps):
            name = f"{eco}:{dep}"
            rows.append({"name": name, "ecosystem": eco})

    g = Graphiti(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "demodemo"),
        store_raw_episode_content=False,
    )

    # Ensure project node exists and is a SoftwareComponent
    q_project = (
        "MERGE (p:Entity {group_id:$gid, name:$pname}) "
        "SET p:SoftwareComponent"
    )
    await g.driver.execute_query(q_project, gid=args.group_id, pname=args.project_name)

    if rows:
        # Create/label dependency components
        q_deps = (
            "UNWIND $rows AS r "
            "MERGE (c:SoftwareComponent:Entity {group_id:$gid, name:r.name}) "
            "ON CREATE SET c.ecosystem = r.ecosystem"
        )
        await g.driver.execute_query(q_deps, rows=rows, gid=args.group_id)

        # Connect project -> deps
        q_edges = (
            "MATCH (p:Entity {group_id:$gid, name:$pname}) "
            "WITH p "
            "UNWIND $rows AS r "
            "MATCH (c:Entity {group_id:$gid, name:r.name}) "
            "MERGE (p)-[:RELATES_TO {group_id:$gid, name:'DEPENDS_ON'}]->(c)"
        )
        await g.driver.execute_query(q_edges, rows=rows, gid=args.group_id, pname=args.project_name)

    print(f"Added/updated {len(rows)} SoftwareComponent dependencies for project '{args.project_name}' in group '{args.group_id}'.")


if __name__ == "__main__":
    asyncio.run(main_async())
