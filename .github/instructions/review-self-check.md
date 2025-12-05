---
description: Pre-PR self-review for AI agent changes
applyTo: "**"
---

# Review Self-Check

- **Ground truth**: Does the change match current code/data, not aspirational docs?
- **Behavior**: Can you explain inputs/outputs and failure modes? Any silent fallbacks?
- **Safety**: Are production paths guarded? Are retries/timeouts/logging in place where needed?
- **Data model**: Do queries/migrations align with existing schemas? No new stores without approval.
- **Tests**: Did you run the smallest relevant tests? Added/updated tests for new behavior?
- **Perf**: Any I/O-heavy work? Using appropriate fast storage? Batching where appropriate?
- **DX**: Names, types, and signatures consistent with existing patterns? Dead code or unused params removed?
- **Docs**: Updated READMEs/guides/inline docstrings when behavior or workflows changed?
