#!/opt/miniforge/envs/casa6/bin/python
"""
Graphiti guardrails checker/fixer for a group.

Checks and (optionally) fixes common hygiene issues:
- Missing uuid/summary on Entity nodes
- Missing or mismatched name embeddings on Entity nodes
- Adds uniqueness constraint on (:Entity {uuid}) if possible

Usage (example):
  uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
    python scripts/graphiti_guardrails_check.py \
    --group-id dsa110-contimg --fix

Notes:
- Loads environment from the Graphiti MCP server .env by default
- Uses the Vertex/Gemini/OpenAI embedder dictated by env via Graphiti MCP server config
- Does not require Neo4j Enterprise (skips existence constraints)
"""
from __future__ import annotations

import argparse
import asyncio
import os
# Ensure the MCP server module is importable for embedder config
import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv
from graphiti_core import Graphiti

sys.path.insert(0, "/home/ubuntu/proj/mcps/graphiti/mcp_server")
# Prefer the embedder selection logic from the MCP server (supports Vertex/OpenAI/Gemini)
from graphiti_mcp_server import GraphitiEmbedderConfig


async def _count(g: Graphiti, cypher: str, **params) -> int:
    recs, _, _ = await g.driver.execute_query(cypher, **params)
    return int(recs[0]["c"]) if recs else 0


async def _backfill_uuid(g: Graphiti, gid: str) -> int:
    recs, _, _ = await g.driver.execute_query(
        """
        MATCH (e:Entity {group_id:$gid})
        WHERE e.uuid IS NULL OR e.uuid = ''
        WITH e SET e.uuid = toString(randomUUID())
        RETURN count(e) AS c
        """,
        gid=gid,
    )
    return int(recs[0]["c"]) if recs else 0


async def _backfill_summary(g: Graphiti, gid: str) -> int:
    recs, _, _ = await g.driver.execute_query(
        """
        MATCH (e:Entity {group_id:$gid})
        WHERE e.summary IS NULL
        WITH e SET e.summary = ''
        RETURN count(e) AS c
        """,
        gid=gid,
    )
    return int(recs[0]["c"]) if recs else 0


async def _ensure_unique_constraint(g: Graphiti) -> None:
    # Drop conflicting range index if present, then add uniqueness constraint
    recs, _, _ = await g.driver.execute_query(
        """
        SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties
        WHERE labelsOrTypes = ['Entity'] AND properties = ['uuid']
        RETURN name, type
        """,
    )
    names = [r["name"] for r in recs]
    if "entity_uuid" in names:
        await g.driver.execute_query("DROP INDEX entity_uuid IF EXISTS")
    try:
        await g.driver.execute_query(
            "CREATE CONSTRAINT entity_uuid_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.uuid IS UNIQUE"
        )
    except Exception:
        # Community-friendly; ignore if not supported
        pass


async def _iter_rows(g: Graphiti, gid: str, where: str, fields: str, batch: int):
    last_uuid: Optional[str] = None
    while True:
        q = (
            f"MATCH (e:Entity {{group_id:$gid}}) WHERE {where} "
            + ("AND e.uuid > $cursor " if last_uuid else "")
            + f"RETURN {fields} ORDER BY e.uuid LIMIT $lim"
        )
        params = {"gid": gid, "lim": batch}
        if last_uuid:
            params["cursor"] = last_uuid
        recs, _, _ = await g.driver.execute_query(q, **params)
        if not recs:
            break
        yield recs
        last_uuid = recs[-1]["uuid"]


async def _reembed_missing_and_mismatched(g: Graphiti, gid: str, target_dim: int, batch: int) -> dict:
    emb = GraphitiEmbedderConfig.from_env().create_client()
    if emb is None:
        return {"updated": 0, "note": "No embedder client available"}

    updated = 0

    # Missing embeddings
    async for recs in _iter_rows(g, gid, "e.name_embedding IS NULL", "e.uuid AS uuid, e.name AS name", batch):
        names = [r["name"].replace("\n", " ") if r["name"] else "" for r in recs]
        vecs: List[List[float]] = await emb.create_batch(names)
        payload: List[Dict] = [{"uuid": r["uuid"], "vec": v} for r, v in zip(recs, vecs, strict=True)]
        await g.driver.execute_query(
            "UNWIND $rows AS row MATCH (n:Entity {uuid: row.uuid}) WITH n, row CALL db.create.setNodeVectorProperty(n, 'name_embedding', row.vec) RETURN 1",
            rows=payload,
        )
        updated += len(payload)

    # Mismatched embeddings
    async for recs in _iter_rows(
        g, gid, f"e.name_embedding IS NOT NULL AND size(e.name_embedding) <> {target_dim}", "e.uuid AS uuid, e.name AS name", batch
    ):
        names = [r["name"].replace("\n", " ") if r["name"] else "" for r in recs]
        vecs: List[List[float]] = await emb.create_batch(names)
        payload: List[Dict] = [{"uuid": r["uuid"], "vec": v} for r, v in zip(recs, vecs, strict=True)]
        await g.driver.execute_query(
            "UNWIND $rows AS row MATCH (n:Entity {uuid: row.uuid}) WITH n, row CALL db.create.setNodeVectorProperty(n, 'name_embedding', row.vec) RETURN 1",
            rows=payload,
        )
        updated += len(payload)

    return {"updated": updated}


async def main_async(env_path: str, group_id: str, fix: bool, batch: int) -> None:
    load_dotenv(env_path)
    g = Graphiti(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "demodemo"),
        store_raw_episode_content=True,
    )

    # Counts
    missing_uuid = await _count(
        g,
        "MATCH (e:Entity {group_id:$gid}) WHERE e.uuid IS NULL OR e.uuid = '' RETURN count(e) AS c",
        gid=group_id,
    )
    missing_summary = await _count(
        g, "MATCH (e:Entity {group_id:$gid}) WHERE e.summary IS NULL RETURN count(e) AS c", gid=group_id
    )
    missing_emb = await _count(
        g, "MATCH (e:Entity {group_id:$gid}) WHERE e.name_embedding IS NULL RETURN count(e) AS c", gid=group_id
    )
    target_dim = int(os.environ.get("EMBEDDING_DIM", 768))
    mismatched_emb = await _count(
        g,
        f"MATCH (e:Entity {{group_id:$gid}}) WHERE e.name_embedding IS NOT NULL AND size(e.name_embedding) <> {target_dim} RETURN count(e) AS c",
        gid=group_id,
    )

    print(f"GROUP={group_id}")
    print(f"MISSING_UUID={missing_uuid}")
    print(f"MISSING_SUMMARY={missing_summary}")
    print(f"MISSING_EMBEDDING={missing_emb}")
    print(f"MISMATCHED_EMBEDDING={mismatched_emb}")

    if not fix:
        return

    total_fixed = {"uuid": 0, "summary": 0, "embeddings": 0}

    if missing_uuid:
        total_fixed["uuid"] = await _backfill_uuid(g, group_id)
    if missing_summary:
        total_fixed["summary"] = await _backfill_summary(g, group_id)

    await _ensure_unique_constraint(g)

    if missing_emb or mismatched_emb:
        res = await _reembed_missing_and_mismatched(g, group_id, target_dim, batch)
        total_fixed["embeddings"] = res.get("updated", 0)

    # Final counts
    missing_uuid2 = await _count(
        g,
        "MATCH (e:Entity {group_id:$gid}) WHERE e.uuid IS NULL OR e.uuid = '' RETURN count(e) AS c",
        gid=group_id,
    )
    missing_summary2 = await _count(
        g, "MATCH (e:Entity {group_id:$gid}) WHERE e.summary IS NULL RETURN count(e) AS c", gid=group_id
    )
    missing_emb2 = await _count(
        g, "MATCH (e:Entity {group_id:$gid}) WHERE e.name_embedding IS NULL RETURN count(e) AS c", gid=group_id
    )
    mismatched_emb2 = await _count(
        g,
        f"MATCH (e:Entity {{group_id:$gid}}) WHERE e.name_embedding IS NOT NULL AND size(e.name_embedding) <> {target_dim} RETURN count(e) AS c",
        gid=group_id,
    )

    print("FIXED_UUID=", total_fixed["uuid"])  # number of nodes altered
    print("FIXED_SUMMARY=", total_fixed["summary"])  # number of nodes altered
    print("FIXED_EMBEDDINGS=", total_fixed["embeddings"])  # number of nodes re-embedded
    print(f"POST_MISSING_UUID={missing_uuid2}")
    print(f"POST_MISSING_SUMMARY={missing_summary2}")
    print(f"POST_MISSING_EMBEDDING={missing_emb2}")
    print(f"POST_MISMATCHED_EMBEDDING={mismatched_emb2}")


def main():
    ap = argparse.ArgumentParser(description="Graphiti guardrails checker/fixer")
    ap.add_argument("--env", default="/home/ubuntu/proj/mcps/graphiti/mcp_server/.env")
    ap.add_argument("--group-id", default="dsa110-contimg")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--batch", type=int, default=200)
    args = ap.parse_args()

    asyncio.run(main_async(args.env, args.group_id, args.fix, args.batch))


if __name__ == "__main__":
    main()
