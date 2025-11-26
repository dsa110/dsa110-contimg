#!/usr/bin/env bash
#
# Frontend Directory Cleanup Script
# ==================================
#
# Consolidates the frontend directory structure
#

set -euo pipefail

FRONTEND_DIR="/data/dsa110-contimg/frontend"

echo "=== Frontend Directory Cleanup ==="

cd "$FRONTEND_DIR"

# 1. Create config directory for frontend-specific configs
echo ""
echo "Phase 1: Consolidate config files → config/"
mkdir -p config/typescript config/vite config/playwright config/docker

# Move TypeScript configs
for f in tsconfig.json tsconfig.app.json tsconfig.node.json; do
    if [[ -f "$f" ]] && [[ ! -L "$f" ]]; then
        mv "$f" config/typescript/
        ln -sf "config/typescript/$f" "$f"
        echo "  Moved $f → config/typescript/"
    fi
done

# Move Vite configs
for f in vite.config.ts vite.config.minimal.ts vitest.config.ts; do
    if [[ -f "$f" ]] && [[ ! -L "$f" ]]; then
        mv "$f" config/vite/
        ln -sf "config/vite/$f" "$f"
        echo "  Moved $f → config/vite/"
    fi
done

# Move Playwright configs  
for f in playwright.config.ts playwright.docker.config.ts playwright.test.config.ts; do
    if [[ -f "$f" ]] && [[ ! -L "$f" ]]; then
        mv "$f" config/playwright/
        ln -sf "config/playwright/$f" "$f"
        echo "  Moved $f → config/playwright/"
    fi
done

# Move Docker configs
for f in Dockerfile.dev Dockerfile.test docker-compose.test.yml nginx.conf; do
    if [[ -f "$f" ]] && [[ ! -L "$f" ]]; then
        mv "$f" config/docker/
        echo "  Moved $f → config/docker/"
    fi
done

# 2. Archive backup files
echo ""
echo "Phase 2: Archive backup files → .archive/"
mkdir -p .archive

for f in *.backup vite.config.ts.backup playwright.config.ts.backup .env.development.backup; do
    if [[ -f "$f" ]]; then
        mv "$f" .archive/
        echo "  Archived $f"
    fi
done

# 3. Move documentation/proposal files to docs
echo ""
echo "Phase 3: Move documentation → docs/"
mkdir -p docs

for f in REORGANIZATION_PROPOSAL.md; do
    if [[ -f "$f" ]]; then
        mv "$f" docs/
        echo "  Moved $f → docs/"
    fi
done

# Move script docs to docs
if [[ -f "scripts/SECURITY.md" ]]; then
    mv scripts/SECURITY.md docs/
    echo "  Moved scripts/SECURITY.md → docs/"
fi

if [[ -f "scripts/STREAMLINED_FIX_APPROACH.md" ]]; then
    mv scripts/STREAMLINED_FIX_APPROACH.md docs/
    echo "  Moved scripts/STREAMLINED_FIX_APPROACH.md → docs/"
fi

if [[ -f "scripts/automated-fixes.md" ]]; then
    mv scripts/automated-fixes.md docs/
    echo "  Moved scripts/automated-fixes.md → docs/"
fi

# 4. Organize scripts by purpose
echo ""
echo "Phase 4: Organize scripts → scripts/{build,dev,test,tools}/"
mkdir -p scripts/build scripts/dev scripts/test scripts/tools

# Build scripts
for f in build-in-scratch.sh install-dependencies.sh install-dependencies-reliable.sh verify-build.sh; do
    if [[ -f "scripts/$f" ]]; then
        mv "scripts/$f" scripts/build/
        echo "  Moved scripts/$f → scripts/build/"
    fi
done

# Dev scripts
for f in start-dev.sh start-dev-safe.sh stop-dev.sh restart-dev.sh manage-dev-server.sh check-dev.sh cleanup-port.sh clear_vite_cache.sh dev-proxy.js vite-dev.service; do
    if [[ -f "scripts/$f" ]]; then
        mv "scripts/$f" scripts/dev/
        echo "  Moved scripts/$f → scripts/dev/"
    elif [[ -f "$f" ]]; then
        mv "$f" scripts/dev/
        echo "  Moved $f → scripts/dev/"
    fi
done

# Test scripts
for f in run-tests.sh test.sh test-skyview.sh verify-tests.sh vitest-wrapper.sh; do
    if [[ -f "scripts/$f" ]]; then
        mv "scripts/$f" scripts/test/
        echo "  Moved scripts/$f → scripts/test/"
    fi
done

# Tools/fix scripts
for f in fix-all-errors.js fix-all-remaining.js fix-remaining-errors.js fix-typescript-errors.js fix-unused-imports.js fix-unused-vars.js check-imports.js verify-page-exports.js setup-crypto.js setup-crypto.cjs check-casa6-node.sh download-js9.sh remove-js9-declarations.py; do
    if [[ -f "scripts/$f" ]]; then
        mv "scripts/$f" scripts/tools/
        echo "  Moved scripts/$f → scripts/tools/"
    fi
done

# Move eslint-rules to tools
if [[ -d "scripts/eslint-rules" ]]; then
    mv scripts/eslint-rules scripts/tools/
    echo "  Moved scripts/eslint-rules → scripts/tools/"
fi

# 5. Clean up empty test directories
echo ""
echo "Phase 5: Clean up empty directories"
for d in tests/integration tests/playwright tests/unit; do
    if [[ -d "$d" ]] && [[ -z "$(ls -A $d 2>/dev/null)" ]]; then
        rmdir "$d"
        echo "  Removed empty: $d"
    fi
done

# 6. Move test-api.html to tests
echo ""
echo "Phase 6: Move test files"
if [[ -f "test-api.html" ]]; then
    mv test-api.html tests/
    echo "  Moved test-api.html → tests/"
fi

# 7. Update package.json scripts to use new paths
echo ""
echo "Phase 7: Create wrapper scripts at root for compatibility"

# Create wrapper for dev-proxy.js
if [[ ! -f "dev-proxy.js" ]] && [[ -f "scripts/dev/dev-proxy.js" ]]; then
    cat > dev-proxy.js << 'EOF'
// Wrapper - actual file is in scripts/dev/dev-proxy.js
module.exports = require('./scripts/dev/dev-proxy.js');
EOF
    echo "  Created dev-proxy.js wrapper"
fi

echo ""
echo "=== Frontend Cleanup Complete ==="
echo ""
echo "New structure:"
echo "  config/       - TypeScript, Vite, Playwright, Docker configs"
echo "  docs/         - Frontend documentation"
echo "  scripts/      - Organized by: build/, dev/, test/, tools/"
echo "  .archive/     - Backup files"
echo ""
