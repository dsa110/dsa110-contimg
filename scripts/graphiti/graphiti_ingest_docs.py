#!/usr/bin/env python3
"""
Ingest core documentation files into the Graphiti knowledge graph and link them
to key scripts via DOCUMENTS edges for easy navigation by agents.

Usage:
  uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
    python /data/dsa110-contimg/scripts/graphiti_ingest_docs.py \
    --root /data/dsa110-contimg --group-id dsa110-contimg

Notes:
  - Loads environment from the Graphiti MCP server .env to get DB creds and embedder.
  - Creates (or updates) :Entity:Documentation:File nodes for selected docs.
  - Embeds node names with the current embedder and sets name_embedding.
  - Creates DOCUMENTS edges from docs to related scripts when both exist.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from graphiti_core import Graphiti

# Reuse embedder selection logic from the MCP server
import sys
sys.path.insert(0, "/home/ubuntu/proj/mcps/graphiti/mcp_server")
from graphiti_mcp_server import GraphitiEmbedderConfig  # type: ignore


DOC_BASENAMES = [
    "README.md",
    "quickstart.md",
    "quicklook.md",
    "pipeline.md",
]

# Map documentation to the scripts they document
DOC_LINKS: Dict[str, List[str]] = {
    "quickstart.md": ["run_conversion.sh", "image_ms.sh"],
    "quicklook.md": ["image_ms.sh"],
    "pipeline.md": ["run_conversion.sh", "calibrate_bandpass.sh"],
    # README can point to the primary entrypoints
    "README.md": ["run_conversion.sh", "image_ms.sh"],
}


async def ingest_docs(root: Path, group_id: str) -> Dict[str, int]:
    load_dotenv("/home/ubuntu/proj/mcps/graphiti/mcp_server/.env")
    g = Graphiti(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "demodemo"),
        store_raw_episode_content=True,
    )

    emb = GraphitiEmbedderConfig.from_env().create_client()
    if emb is None:
        raise RuntimeError("No embedder available; ensure API keys are set in .env")

    # Discover documentation files under root
    candidates: List[Path] = []
    for bn in DOC_BASENAMES:
        # Search both top-level and docs/
        for rel in [Path(bn), Path("docs") / bn, Path("docs/pipeline") / bn]:
            p = (root / rel)
            if p.exists() and p.is_file():
                candidates.append(p)
                break

    if not candidates:
        return {"ingested": 0, "linked": 0}

    # Prepare payload for MERGE and embeddings
    names = [p.name for p in candidates]
    vecs = await emb.create_batch(names)

    rows = [
        {
            "name": p.name,
            "group_id": group_id,
            "path": str(p.relative_to(root)),
            "labels": ["Entity", "Documentation", "File"],
            "summary": "",
            "uuid": None,
            "created_at": None,
            "vec": v,
        }
        for p, v in zip(candidates, vecs, strict=True)
    ]

    # Upsert nodes and set vector property
    await g.driver.execute_query(
        """
        UNWIND $rows AS row
        MERGE (n:Entity {group_id: row.group_id, name: row.name})
        SET n:Documentation:File,
            n.summary = coalesce(n.summary, row.summary),
            n.path = row.path
        WITH n, row
        CALL db.create.setNodeVectorProperty(n, 'name_embedding', row.vec)
        RETURN count(n) AS c
        """,
        rows=rows,
    )

    # Create DOCUMENTS edges using the mapping
    linked = 0
    for bn, targets in DOC_LINKS.items():
        for t in targets:
            recs, _, _ = await g.driver.execute_query(
                """
                MATCH (d:Entity:Documentation {group_id:$gid, name:$doc}),
                      (s:Entity {group_id:$gid, name:$script})
                MERGE (d)-[:RELATES_TO {name:'DOCUMENTS', group_id:$gid}]->(s)
                RETURN 1 AS ok
                """,
                gid=group_id,
                doc=bn,
                script=t,
            )
            if recs:
                linked += 1

    return {"ingested": len(rows), "linked": linked}


def main():
    ap = argparse.ArgumentParser(description="Ingest core docs and link to scripts")
    ap.add_argument("--root", default="/data/dsa110-contimg")
    ap.add_argument("--group-id", default="dsa110-contimg")
    args = ap.parse_args()
    res = asyncio.run(ingest_docs(Path(args.root), args.group_id))
    print(f"INGESTED={res['ingested']}")
    print(f"DOC_LINKS_CREATED={res['linked']}")


if __name__ == "__main__":
    main()

