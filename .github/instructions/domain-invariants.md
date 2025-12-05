---
description: Domain invariants and constants for this project
applyTo: '**'
---

# Domain Invariants

- **Cardinality and grouping**: Know the required batch size or grouping rules; avoid processing partial sets that violate domain assumptions.
- **Normalization**: Use canonical naming/normalization rules before grouping or indexing; avoid ad-hoc filename parsing.
- **Active code paths**: Work in the current codebase, not legacy directories. Confirm which modules are authoritative.
- **Data stores**: Identify production databases and indexes; query them instead of scanning file systems. Treat production stores as read-mostly unless change is intentional and reviewed.
- **Storage tiers**: Understand which locations are production, scratch, or temporary. Keep heavy I/O off slow or production-only storage.
- **Compatibility**: Respect the project’s runtime versions and required flags; avoid changing them without approval.
- **Reference data**: Use shared utilities/constants for domain data instead of hardcoding values.
- **Naming conventions**: Follow established naming schemes for fields/records; understand any auto-renaming rules before overriding.
- **Writers/adapters**: Use supported writers/adapters for outputs; keep test-only components in tests.
- **Environments**: Activate the expected environment/toolchain before running commands.
- **Safety**: Treat production state carefully; avoid destructive operations without backups and approvals.
