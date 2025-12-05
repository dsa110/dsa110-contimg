# DSA-110 Configuration Files

Configuration files for development tools and services.

## Structure

- `hooks/` - Git hooks (husky). Root `.husky/` symlinks here.
- `environment-pins.txt` - Python environment version pins (e.g., setuptools<81 for CASA compatibility)
- `ragflow.env` - RAGFlow MCP server configuration

## Symlinks

- `/.husky` → `config/hooks/husky` (git hooks path configured in `.git/config`)

## Related

- Docker configs: `ops/docker/`
- Operational scripts: `scripts/ops/`
