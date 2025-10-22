#!/usr/bin/env python3
"""
Re-embed Graphiti nodes and edges that have mismatched (legacy) embedding dimensions.

Defaults:
- Detects embeddings with size=768 and regenerates at the current embedder dimension
  (default 1024, configurable via EMBEDDING_DIM env for graphiti_core).

Usage:
  uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
    python /data/dsa110-contimg/scripts/graphiti_reembed_mismatched.py \
    --group-id dsa110-contimg

Notes:
- Requires the Graphiti MCP server project to provide dependencies (graphiti_core).
- Loads env from /home/ubuntu/proj/mcps/graphiti/mcp_server/.env for DB creds and API keys.
- If no embedder API key is available, the script can optionally just null-out legacy vectors
  to avoid runtime errors during similarity search.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from typing import Iterable

from dotenv import load_dotenv

from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, create_entity_node_embeddings
from graphiti_core.edges import EntityEdge, create_entity_edge_embeddings


async def _chunked(it: Iterable[str], size: int):
    buf: list[str] = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


async def reembed(g: Graphiti, group_id: str | None, legacy_dim: int, batch: int) -> tuple[int, int]:
    node_count = 0
    edge_count = 0

    group_cond = " AND n.group_id = $group_id" if group_id else ""
    edge_group_cond = " AND e.group_id = $group_id" if group_id else ""

    # Collect node uuids to re-embed
    q_nodes = (
        "MATCH (n:Entity) WHERE n.name_embedding IS NOT NULL "
        f"AND size(n.name_embedding) = {legacy_dim}"
        + group_cond
        + " RETURN n.uuid AS uuid"
    )
    recs, _, _ = await g.driver.execute_query(q_nodes, group_id=group_id, routing_='r')
    node_uuids = [r["uuid"] for r in recs]

    # Collect edge uuids to re-embed
    q_edges = (
        "MATCH ()-[e:RELATES_TO]->() WHERE e.fact_embedding IS NOT NULL "
        f"AND size(e.fact_embedding) = {legacy_dim}"
        + edge_group_cond
        + " RETURN e.uuid AS uuid"
    )
    recs, _, _ = await g.driver.execute_query(q_edges, group_id=group_id, routing_='r')
    edge_uuids = [r["uuid"] for r in recs]

    # Nodes
    for chunk in [c async for c in _chunked(node_uuids, batch)]:
        nodes = await EntityNode.get_by_uuids(g.driver, chunk)
        await create_entity_node_embeddings(g.embedder, nodes)
        for n in nodes:
            await n.save(g.driver)
            node_count += 1

    # Edges
    for chunk in [c async for c in _chunked(edge_uuids, batch)]:
        edges = await EntityEdge.get_by_uuids(g.driver, chunk)
        await create_entity_edge_embeddings(g.embedder, edges)
        for e in edges:
            await e.save(g.driver)
            edge_count += 1

    return node_count, edge_count


async def null_legacy_vectors(g: Graphiti, group_id: str | None, legacy_dim: int) -> tuple[int, int, int]:
    group_cond = " AND n.group_id = $group_id" if group_id else ""
    edge_group_cond = " AND e.group_id = $group_id" if group_id else ""
    comm_group_cond = " AND c.group_id = $group_id" if group_id else ""

    recs, _, _ = await g.driver.execute_query(
        f"MATCH (n:Entity) WHERE size(n.name_embedding) = {legacy_dim}"
        + group_cond
        + " SET n.name_embedding = NULL RETURN count(n) as c",
        group_id=group_id,
    )
    n = recs[0]["c"] if recs else 0

    recs, _, _ = await g.driver.execute_query(
        f"MATCH ()-[e:RELATES_TO]->() WHERE size(e.fact_embedding) = {legacy_dim}"
        + edge_group_cond
        + " SET e.fact_embedding = NULL RETURN count(e) as c",
        group_id=group_id,
    )
    e = recs[0]["c"] if recs else 0

    recs, _, _ = await g.driver.execute_query(
        f"MATCH (c:Community) WHERE size(c.name_embedding) = {legacy_dim}"
        + comm_group_cond
        + " SET c.name_embedding = NULL RETURN count(c) as c",
        group_id=group_id,
    )
    c = recs[0]["c"] if recs else 0

    return n, e, c


def main():
    ap = argparse.ArgumentParser(description="Re-embed legacy-dimension vectors in Graphiti")
    ap.add_argument("--env", default="/home/ubuntu/proj/mcps/graphiti/mcp_server/.env")
    ap.add_argument("--group-id", default=None)
    ap.add_argument("--legacy-dim", type=int, default=768)
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--null-only", action="store_true", help="Only null-out legacy vectors without re-embedding")
    args = ap.parse_args()

    load_dotenv(args.env)

    # Construct Graphiti (uses env for creds and API keys)
    g = Graphiti(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "demodemo"),
        store_raw_episode_content=True,
    )

    # If no API key for embedder is present and not null-only, switch to null-only
    has_key = any(
        os.environ.get(k)
        for k in ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "GOOGLE_API_KEY", "VOYAGE_API_KEY")
    )

    if args.null_only or not has_key:
        n, e, c = asyncio.run(null_legacy_vectors(g, args.group_id, args.legacy_dim))
        print(f"Nullified legacy-dim vectors: nodes={n}, edges={e}, communities={c}")
        if not has_key and not args.null_only:
            print("Warning: No embedding API key found; performed null-only cleanup. Re-run with a key to re-embed.")
        return

    # Re-embed path
    n, e = asyncio.run(reembed(g, args.group_id, args.legacy_dim, args.batch))
    print(f"Re-embedded: nodes={n}, edges={e}")


if __name__ == "__main__":
    main()

