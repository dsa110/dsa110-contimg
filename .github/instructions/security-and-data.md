---
description: Security, data handling, and operational safety
applyTo: "**"
---

# Security and Data Handling

- **Databases**: Use approved data stores only; avoid ad-hoc CSV/TXT stores. Keep production databases in their designated locations.
- **Production data**: Treat production state as read-mostly unless a change is intentional and reviewed.
- **Paths**: Do not create new top-level directories; follow existing storage conventions.
- **Secrets**: Do not hardcode credentials; use environment/config. Avoid logging secrets or sensitive data.
- **Network**: Prefer local resources; avoid external calls unless required and approved.
- **Validation**: Validate inputs early (filenames, IDs, parameters); reject invalid inputs clearly.
- **Error handling**: Use structured logging and explicit error codes. Avoid silent exceptions; raise or return clear errors.
- **Migrations**: Back up databases before schema changes; prefer additive migrations. Confirm counts before/after.
- **Downloads/build artifacts**: Use temporary/scratch storage; clean up temp files.
