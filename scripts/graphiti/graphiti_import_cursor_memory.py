#!/opt/miniforge/envs/casa6/bin/python
"""
Import a Cursor agent-memory export (JSON) into the Graphiti knowledge graph (Neo4j).

The input file is produced by Cursor's generic memory MCP and contains two arrays:
  - entities: [{ name, entityType, observations? }]
  - relations: [{ from, to, relationType }]

This script maps those into Graphiti Entity nodes and RELATES_TO edges by using
graphiti_core's high-level API. It reuses your existing Graphiti MCP server
environment (.env) so the data lands in the same Neo4j and group namespace.

Usage:
  uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
    python /data/dsa110-contimg/scripts/graphiti_import_cursor_memory.py \
    --input \
    /data/dsa110-contimg/.cursor/.agent-tools/8d9aa307-55ae-435e-8eab-ac4a77da4f01.txt \
    --group-id openai

Notes:
  - Requires the Graphiti MCP server project to provide dependencies (run via `uv run` as above).
  - Loads env from /home/ubuntu/proj/mcps/graphiti/mcp_server/.env for Neo4j creds and API keys.
  - By default, uses OpenAI clients from graphiti_core if LLM/embedder are not provided.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from dotenv import load_dotenv
# Import Graphiti core
from graphiti_core import Graphiti
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode


def load_input(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some Cursor exports may be JSON-without-newline at EOF; rethrow
        raise


def _scan_repo(root: Path, exts: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Scan a repository tree and emit a simple entities/relations structure.

    - Directories become `Module` entities
    - Files become `File` entities (filtered by exts if provided)
    - Root becomes `Project`
    - Edges:
      Project --CONTAINS_MODULE--> top-level dirs
      Module  --CONTAINS_MODULE--> subdirs
      Module  --CONTAINS_FILE--> files
    """
    root = root.resolve()
    project_name = root.name

    ents: Dict[str, Dict[str, Any]] = {}
    rels: list[Dict[str, str]] = []

    def put_entity(name: str, etype: str) -> None:
        entry = ents.setdefault(
            name,
            {
                "type": "entity",
                "name": name,
                "labels": set(),
            },
        )
        if etype:
            entry["labels"].add(etype)

    put_entity(project_name, "Project")

    include_file = (lambda p: True)
    if exts:
        exts_l = {e.lower() for e in exts}

        def _inc(p: Path) -> bool:
            return p.suffix.lower() in exts_l

        include_file = _inc

    for dirpath, dirnames, filenames in os.walk(root):
        dpath = Path(dirpath)
        if any(part.startswith('.')
               for part in dpath.parts if part not in ('.',)):
            # Skip hidden dirs like .git/.cursor
            continue
        parent_name = dpath.name if dpath != root else project_name
        # Register this directory as Module (skip root which is Project)
        if dpath != root:
            put_entity(dpath.name, "Module")
        # Parent to children directories
        for child in list(dirnames):
            if child.startswith('.'):
                continue
            put_entity(child, "Module")
            rels.append({"type": "relation", "from": parent_name,
                        "to": child, "relationType": "CONTAINS_MODULE"})
        # Files
        for fn in filenames:
            if fn.startswith('.'):
                continue

            if fn == "Dockerfile":
                put_entity(fn, "ConfigurationFile")
                build_process_name = f"BuildProcess_{fn}"
                put_entity(build_process_name, "BuildProcess")
                rels.append({"type": "relation",
                             "from": build_process_name,
                             "to": fn,
                             "relationType": "DEFINED_IN"})

                # Extract base image from Dockerfile
                try:
                    with open(dpath / fn) as f:
                        for line in f:
                            if line.strip().upper().startswith("FROM"):
                                base_image = line.strip().split()[1]
                                put_entity(base_image, "ContainerImage")
                                # The base image is also a software component
                                put_entity(base_image, "SoftwareComponent")
                                rels.append({"type": "relation",
                                             "from": base_image,
                                             "to": build_process_name,
                                             "relationType": "BUILT_FROM"})
                                # An image contains itself as a component
                                rels.append({"type": "relation",
                                             "from": base_image,
                                             "to": base_image,
                                             "relationType": "CONTAINS"})
                                break  # Assume first FROM is the base
                except Exception as e:
                    print(f"Could not parse {dpath / fn}: {e}")
            else:
                fpath = dpath / fn
                if not include_file(fpath):
                    continue
                put_entity(fn, "File")
                rels.append({"type": "relation",
                             "from": dpath.name if dpath != root else project_name,
                             "to": fn,
                             "relationType": "CONTAINS_FILE"})

    # Normalize label sets to sorted lists for downstream consumers
    for entry in ents.values():
        labels = entry.get("labels", set())
        if isinstance(labels, set):
            entry["labels"] = sorted(labels)

    return {"entities": list(ents.values()), "relations": rels}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Import Cursor memory JSON to Graphiti/Neo4j")
    ap.add_argument(
        "--input",
        type=Path,
        help="Path to Cursor memory JSON file")
    ap.add_argument(
        "--group-id",
        default="openai",
        help="Graph group_id namespace")
    ap.add_argument(
        "--env",
        default="/home/ubuntu/proj/mcps/graphiti/mcp_server/.env",
        help=".env to load for Neo4j/API keys")
    ap.add_argument(
        "--scan-root",
        type=Path,
        help="If provided, scan this repo root and import module/file relationships.")
    ap.add_argument(
        "--scan-exts",
        nargs='*',
        default=[
            ".py",
            ".md",
            ".yaml",
            ".yml",
            ".json",
            ".sh",
            ".ipynb"],
        help="File extensions to include when scanning.")
    ap.add_argument(
        "--fast-no-llm",
        action="store_true",
        help="Use direct Neo4j MERGE without embeddings or LLM reasoning (much faster for large imports).")
    args = ap.parse_args()

    # Load env so Graphiti can connect to Neo4j and LLM/embedder providers
    load_dotenv(args.env)

    entities: list[Dict[str, Any]] = []
    relations: list[Dict[str, Any]] = []

    if args.input:
        data = load_input(args.input)
        entities.extend(data.get("entities", []))
        relations.extend(data.get("relations", []))

    if args.scan_root:
        scanned = _scan_repo(args.scan_root, set(args.scan_exts or []))
        entities.extend(scanned.get("entities", []))
        relations.extend(scanned.get("relations", []))

    # Connect to Neo4j using defaults from environment
    # (Graphiti falls back to OpenAI clients if not provided explicitly.)
    g = Graphiti(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "demodemo"),
        store_raw_episode_content=True,
    )

    now = datetime.now(timezone.utc)

    # Pre-create EntityNode shells keyed by (name)
    node_cache: Dict[str, EntityNode] = {}
    for e in entities:
        name = e.get("name")
        if not name:
            continue
        labels = list(e.get("labels", []))
        etype = e.get("entityType")
        if isinstance(etype, str) and etype and etype not in labels:
            labels.append(etype)
        node_cache[name] = EntityNode(
            name=name,
            group_id=args.group_id,
            labels=labels,
            attributes={
                "source": "cursor-agent-memory",
                "entityType": etype or ""},
        )

    async def import_async():
        # Create edges via add_triplet (handles node resolution/merge and
        # embeddings)
        added = 0
        for rel in relations:
            src = rel.get("from")
            dst = rel.get("to")
            rname = rel.get("relationType") or rel.get("type") or "RELATED_TO"
            if not src or not dst:
                continue
            s_node = node_cache.get(src) or EntityNode(
                name=src, group_id=args.group_id, labels=[])
            t_node = node_cache.get(dst) or EntityNode(
                name=dst, group_id=args.group_id, labels=[])
            fact = f"{src} {rname} {dst}"
            edge = EntityEdge(
                group_id=args.group_id,
                source_node_uuid=s_node.uuid,
                target_node_uuid=t_node.uuid,
                created_at=now,
                valid_at=now,
                name=rname,
                fact=fact,
            )
            await g.add_triplet(s_node, edge, t_node)
            added += 1
        return added

    async def fast_import_async():
        """Import using direct MERGE without LLM/embeddings for speed."""
        from uuid import uuid4

        gid = args.group_id
        # Prepare batches
        ent_batch = []
        seen = set()
        for name, node in node_cache.items():
            if name in seen:
                continue
            seen.add(name)
            ent_batch.append({"name": name, "labels": node.labels})

        edge_batch = []
        for rel in relations:
            src = rel.get("from")
            dst = rel.get("to")
            rname = rel.get("relationType") or rel.get("type") or "RELATED_TO"
            if not src or not dst:
                continue
            edge_batch.append({
                "src": src,
                "dst": dst,
                "rname": rname,
                "fact": f"{src} {rname} {dst}",
                "uuid": str(uuid4()),
            })

        async def run_nodes_by_group(batch):
            if not batch:
                return

            # Group entities by their label set
            grouped_ents = defaultdict(list)
            for item in batch:
                # Ensure 'Entity' is always a label and sort for consistent
                # keys
                labels = sorted(
                    list(set((item.get("labels") or []) + ["Entity"])))
                grouped_ents[tuple(labels)].append(item["name"])

            # Run one MERGE query per label group
            for labels, names in grouped_ents.items():
                # Sanitize labels and construct the label suffix for the query
                safe_labels = [
                    re.sub(
                        r'[^A-Za-z0-9_]',
                        '_',
                        l or '') for l in labels]
                label_suffix = ":" + ":".join(safe_labels)

                q = (
                    f"UNWIND $names AS name "
                    f"MERGE (n{label_suffix} {{group_id:$gid, name:name}}) "
                    f"ON CREATE SET n.created_at=datetime()"
                )
                await g.driver.execute_query(q, names=names, gid=gid)

        async def run_edges(batch):
            if not batch:
                return
            q = (
                "UNWIND $batch AS ed "
                "MATCH (s:Entity {group_id:$gid, name:ed.src}), (t:Entity {group_id:$gid, name:ed.dst}) "
                "MERGE (s)-[r:RELATES_TO {uuid:ed.uuid}]->(t) "
                "ON CREATE SET r.group_id=$gid, r.name=ed.rname, r.fact=ed.fact, r.created_at=datetime(), r.valid_at=datetime()")
            await g.driver.execute_query(q, batch=batch, gid=gid)

        # Chunking
        CHUNK = 200
        for i in range(0, len(ent_batch), CHUNK):
            await run_nodes_by_group(ent_batch[i:i + CHUNK])
        for i in range(0, len(edge_batch), CHUNK):
            await run_edges(edge_batch[i:i + CHUNK])
        return len(edge_batch)

    # Run the async import
    if args.fast_no_llm:
        added = asyncio.run(fast_import_async())
        print(
            f"[FAST] Imported {len(entities)} entities referenced and {added} relations into group_id='{args.group_id}'.")
    else:
        added = asyncio.run(import_async())
        print(
            f"Imported {len(entities)} entities referenced and {added} relations into group_id='{args.group_id}'.")


if __name__ == "__main__":
    main()
