# Graphiti Guardrails & Protocol

These conventions keep the `dsa110-contimg` Graphiti knowledge graph healthy and easy to navigate for agents, contributors, and tools.

## Hygiene checks and fixes

- Script: `scripts/graphiti_guardrails_check.py`
- Checks per group:
  - Missing `uuid`
  - Missing `summary`
  - Missing or mismatched `name_embedding`
- Fix mode (`--fix`):
  - Backfills `uuid` and `summary`
  - Re-embeds missing/mismatched vectors using the current embedder from your Graphiti MCP server environment
  - Ensures uniqueness constraint on `(:Entity {uuid})` (Community‑compatible)

Example:

```
uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
  python scripts/graphiti_guardrails_check.py --group-id dsa110-contimg --fix
```

## Embedding dimension change protocol

1. Update `/home/ubuntu/proj/mcps/graphiti/mcp_server/.env` with the target embedder and dimension (e.g., `EMBEDDER_MODEL_NAME`, `EMBEDDING_DIM`).
2. Re-embed vectors for the affected group:
   - Fast path (handles missing + mismatched):
     - `uv run --isolated --directory /home/ubuntu/proj/mcps/graphiti/mcp_server \
        python scripts/graphiti_guardrails_check.py --group-id dsa110-contimg --fix`
   - Legacy-only script:
     - `scripts/graphiti_reembed_mismatched.py --group-id dsa110-contimg --legacy-dim <OLD_DIM>`
3. Validate with the checker (no `--fix`) to confirm zero missing/mismatched.

## Project entry and labels

- `(:Entity:Project {name:'dsa110-contimg'})` anchors navigation.
- Project has `CONTAINS_MODULE` and `CONTAINS_FILE` edges to modules/files in the group.
- Labels promoted for discovery: `File`, `Script`, `ConfigurationFile`, `ContainerImage`.

## Neo4j constraints

- Uniqueness on `Entity.uuid` is enabled.
- Property‑existence constraints require Neo4j Enterprise; use the hygiene script to backfill instead.
