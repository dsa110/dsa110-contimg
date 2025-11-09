# Knowledge Graph Guardrails & Protocol

These conventions keep the `dsa110-contimg` knowledge graph healthy and easy to navigate for contributors and tools.

## Hygiene checks and fixes

- Use the project's guardrail checker to validate and repair common issues.
- Checks per group:
  - Missing `uuid`
  - Missing `summary`
  - Missing or mismatched `name_embedding`
- Fix mode (`--fix`):
  - Backfills `uuid` and `summary`
  - Re-embeds missing/mismatched vectors using the current embedder configured for your knowledge graph service
  - Ensures uniqueness constraint on `(:Entity {uuid})` (Community‑compatible)

Refer to contributor resources for the exact invocation and environment.

## Embedding dimension change protocol

1. Update your knowledge graph service configuration with the target embedder and dimension (e.g., `EMBEDDER_MODEL_NAME` and `EMBEDDING_DIM`).
2. Re-embed vectors for the affected group using the project’s guardrail tooling.
3. Validate with the checker (no `--fix`) to confirm zero missing/mismatched.

## Project entry and labels

- `(:Entity:Project {name:'dsa110-contimg'})` anchors navigation.
- Project has `CONTAINS_MODULE` and `CONTAINS_FILE` edges to modules/files in the group.
- Labels promoted for discovery: `File`, `Script`, `ConfigurationFile`, `ContainerImage`.

## Neo4j constraints

- Uniqueness on `Entity.uuid` is enabled.
- Property‑existence constraints require Neo4j Enterprise; use the hygiene script to backfill instead.
