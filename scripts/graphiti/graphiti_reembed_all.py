#!/usr/bin/env python3
"""
Re-embed all nodes and edges to the active embedder's dimension, fixing NULLs and mismatches.

This script uses the Graphiti MCP server's embedder configuration (preferring Vertex/Gemini when available)
to ensure embeddings are generated with your desired Google stack.

Usage:
  uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
    python /data/dsa110-contimg/scripts/graphiti_reembed_all.py \
    --group-id dsa110-contimg --batch 200

Environment:
  Loads /home/ubuntu/proj/mcps/graphiti/mcp_server/.env for Neo4j/Google credentials.
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

# Import embedder config from the MCP server to honor Vertex/Gemini preferences
from graphiti_mcp_server import GraphitiEmbedderConfig


async def _chunked(it: Iterable[str], size: int):
    buf: list[str] = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


async def reembed_all(g: Graphiti, group_id: str | None, target_dim: int, batch: int) -> tuple[int, int]:
    """Fast re-embed using direct Cypher updates to avoid validation issues."""
    node_count = 0
    edge_count = 0

    group_cond_n = " AND n.group_id = $group_id" if group_id else ""
    group_cond_e = " AND e.group_id = $group_id" if group_id else ""

    # Nodes: fetch UUID + name where missing/wrong dim
    q_nodes = (
        "MATCH (n:Entity) WHERE (n.name_embedding IS NULL OR size(n.name_embedding) <> $target_dim)"
        + group_cond_n
        + " RETURN n.uuid AS uuid, n.name AS name"
    )
    recs, _, _ = await g.driver.execute_query(q_nodes, group_id=group_id, target_dim=target_dim, routing_='r')
    node_rows = [{"uuid": r["uuid"], "name": r["name"]} for r in recs if r.get("name")]

    # Edges: fetch UUID + fact where missing/wrong dim
    q_edges = (
        "MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity) "
        "WHERE (e.fact_embedding IS NULL OR size(e.fact_embedding) <> $target_dim)"
        + group_cond_e
        + " RETURN e.uuid AS uuid, e.fact AS fact"
    )
    recs, _, _ = await g.driver.execute_query(q_edges, group_id=group_id, target_dim=target_dim, routing_='r')
    edge_rows = [{"uuid": r["uuid"], "fact": r["fact"]} for r in recs if r.get("fact")]

    # Embed and update nodes in batches
    for i in range(0, len(node_rows), batch):
        chunk = node_rows[i:i+batch]
        embeddings = await g.embedder.create_batch([row["name"].replace("\n", " ") for row in chunk])
        payload = [
            {"uuid": row["uuid"], "embedding": emb}
            for row, emb in zip(chunk, embeddings)
        ]
        await g.driver.execute_query(
            "UNWIND $rows AS r MATCH (n:Entity {uuid: r.uuid}) SET n.name_embedding = r.embedding",
            rows=payload,
        )
        node_count += len(payload)

    # Embed and update edges in batches
    for i in range(0, len(edge_rows), batch):
        chunk = edge_rows[i:i+batch]
        embeddings = await g.embedder.create_batch([row["fact"].replace("\n", " ") for row in chunk])
        payload = [
            {"uuid": row["uuid"], "embedding": emb}
            for row, emb in zip(chunk, embeddings)
        ]
        await g.driver.execute_query(
            "UNWIND $rows AS r MATCH ()-[e:RELATES_TO {uuid: r.uuid}]->() SET e.fact_embedding = r.embedding",
            rows=payload,
        )
        edge_count += len(payload)

    return node_count, edge_count


def main():
    ap = argparse.ArgumentParser(description="Re-embed all nodes/edges to the active embedder's dimension")
    ap.add_argument("--env", default="/home/ubuntu/proj/mcps/graphiti/mcp_server/.env")
    ap.add_argument("--group-id", default=None)
    ap.add_argument("--batch", type=int, default=200)
    args = ap.parse_args()

    load_dotenv(args.env)

    # Create embedder via MCP server config (prefers Vertex/Gemini)
    embedder_client = GraphitiEmbedderConfig.from_env().create_client()
    if embedder_client is None:
        raise SystemExit("No embedder configured. Ensure Google/Gemini/Vertex credentials are set.")

    # Detect target dimension with a probe
    import asyncio as _asyncio
    target_dim = len(_asyncio.get_event_loop().run_until_complete(embedder_client.create("dimension probe")))

    g = Graphiti(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "demodemo"),
        embedder=embedder_client,
        store_raw_episode_content=True,
    )

    n, e = asyncio.run(reembed_all(g, args.group_id, target_dim, args.batch))
    print(f"Re-embedded to dim={target_dim}: nodes={n}, edges={e}")


if __name__ == "__main__":
    main()
