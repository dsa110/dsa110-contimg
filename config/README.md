# DSA-110 Configuration Files

Consolidated configuration files. Symlinks are maintained at the root for tool compatibility.

## Structure

- `linting/` - Code linting configs (.flake8, .prettierrc, eslint)
- `hooks/` - Git hooks (pre-commit, husky)
- `docker/` - Docker/compose files
- `editor/` - Editor settings (.editorconfig, .nvmrc)
- `environment-pins.txt` - Python environment version pins

## Note

Most tools expect config files at the repository root. Symlinks are created automatically
to maintain compatibility while keeping the actual files organized here.
