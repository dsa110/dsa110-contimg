#!/usr/bin/env bash
#
# DSA-110 Directory Reorganization Script
# ========================================
#
# This script reorganizes the /data/dsa110-contimg/ directory structure
# to simplify development of the frontend dashboard and pipeline.
#
# SAFETY FEATURES:
# - Dry-run mode by default (use --execute to actually move files)
# - Creates rollback script before making changes
# - Uses git mv where possible to preserve history
# - Validates paths before operations
#
# PHASES:
#   1. Consolidate AI Configurations → .ai/
#   2. Consolidate Documentation → docs/
#   3. Consolidate External Dependencies → vendor/
#   4. Clean Up Root Level
#   5. Consolidate Scripts → scripts/
#   6. Consolidate Config Files → config/
#   7. Consolidate State Directories → state/
#   8. Clean Up Hidden Directories
#   9. Restructure Ops Directory
#  10. Create Products Symlinks
#  11. Remove Empty Directories
#  12. Create Compatibility Symlinks
#
# Usage:
#   ./reorganize.sh --dry-run    # Preview changes (default)
#   ./reorganize.sh --execute    # Actually perform the moves
#   ./reorganize.sh --rollback   # Undo the changes (if rollback script exists)
#   ./reorganize.sh --phase N    # Run only phase N (can combine with --dry-run)
#

set -euo pipefail

# Configuration
ROOT_DIR="/data/dsa110-contimg"
ROLLBACK_FILE="${ROOT_DIR}/.local/reorganize_rollback_$(date +%Y%m%d_%H%M%S).sh"
LOG_FILE="${ROOT_DIR}/.local/reorganize_$(date +%Y%m%d_%H%M%S).log"
DRY_RUN=true
ROLLBACK=false
PHASE_FILTER=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --execute)
            DRY_RUN=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --phase)
            PHASE_FILTER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run|--execute|--rollback] [--phase N]"
            exit 1
            ;;
    esac
done

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)   echo -e "${BLUE}[INFO]${NC} $message" ;;
        OK)     echo -e "${GREEN}[OK]${NC} $message" ;;
        WARN)   echo -e "${YELLOW}[WARN]${NC} $message" ;;
        ERROR)  echo -e "${RED}[ERROR]${NC} $message" ;;
        DRY)    echo -e "${YELLOW}[DRY-RUN]${NC} $message" ;;
        PHASE)  echo -e "${CYAN}[PHASE]${NC} $message" ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE" 2>/dev/null || true
}

# Check if we should run a phase
should_run_phase() {
    local phase_num=$1
    if [[ -z "$PHASE_FILTER" ]]; then
        return 0  # Run all phases
    fi
    [[ "$PHASE_FILTER" == "$phase_num" ]]
}

# Function to safely move a directory or file
move_dir() {
    local src="$1"
    local dst="$2"
    local description="${3:-Moving $src to $dst}"
    
    # Check if source exists
    if [[ ! -e "$src" ]]; then
        log WARN "Source does not exist: $src"
        return 0
    fi
    
    # Check if destination already exists
    if [[ -e "$dst" ]]; then
        log WARN "Destination already exists: $dst (skipping)"
        return 0
    fi
    
    # Create parent directory if needed
    local dst_parent=$(dirname "$dst")
    
    if $DRY_RUN; then
        log DRY "$description"
        log DRY "  mkdir -p $dst_parent"
        log DRY "  git mv $src $dst (or mv if not in git)"
        # Record rollback command
        echo "# Rollback: $description" >> "${ROLLBACK_FILE}.preview"
        echo "mv '$dst' '$src'" >> "${ROLLBACK_FILE}.preview"
    else
        log INFO "$description"
        mkdir -p "$dst_parent"
        
        # Try git mv first, fall back to regular mv
        if git -C "$ROOT_DIR" ls-files --error-unmatch "$src" >/dev/null 2>&1; then
            git -C "$ROOT_DIR" mv "$src" "$dst"
            log OK "git mv $src → $dst"
        else
            mv "$src" "$dst"
            log OK "mv $src → $dst"
        fi
        
        # Record rollback command
        echo "mv '$dst' '$src'" >> "$ROLLBACK_FILE"
    fi
}

# Function to create a symlink
create_symlink() {
    local target="$1"
    local link="$2"
    local description="${3:-Creating symlink $link → $target}"
    
    if $DRY_RUN; then
        log DRY "$description"
        log DRY "  ln -sf $target $link"
        echo "# Rollback: $description" >> "${ROLLBACK_FILE}.preview"
        echo "rm -f '$link'" >> "${ROLLBACK_FILE}.preview"
    else
        log INFO "$description"
        if [[ -L "$link" ]]; then
            rm "$link"
        fi
        ln -sf "$target" "$link"
        log OK "Created symlink: $link → $target"
        echo "rm -f '$link'" >> "$ROLLBACK_FILE"
    fi
}

# Function to remove empty directories
remove_empty_dirs() {
    local dir="$1"
    
    if [[ ! -d "$dir" ]]; then
        return 0
    fi
    
    # Find and remove empty directories (depth-first)
    find "$dir" -depth -type d -empty -print 2>/dev/null | while read -r empty_dir; do
        if $DRY_RUN; then
            log DRY "Would remove empty directory: $empty_dir"
        else
            rmdir "$empty_dir" 2>/dev/null && log OK "Removed empty: $empty_dir" || true
        fi
    done
}

# Function to ensure directory exists
ensure_dir() {
    local dir="$1"
    if $DRY_RUN; then
        log DRY "mkdir -p $dir"
    else
        mkdir -p "$dir"
    fi
}

# =========================================
# PHASE 1: Consolidate AI Configurations
# =========================================
phase_1_ai_configs() {
    log PHASE "=== Phase 1: Consolidate AI Configurations → .ai/ ==="
    
    ensure_dir "$ROOT_DIR/.ai"
    
    # Move AI tool directories
    move_dir "$ROOT_DIR/.cursor" "$ROOT_DIR/.ai/cursor" "Moving Cursor config to .ai/"
    move_dir "$ROOT_DIR/.codex" "$ROOT_DIR/.ai/codex" "Moving Codex config to .ai/"
    move_dir "$ROOT_DIR/.gemini" "$ROOT_DIR/.ai/gemini" "Moving Gemini config to .ai/"
    move_dir "$ROOT_DIR/.serena" "$ROOT_DIR/.ai/serena" "Moving Serena config to .ai/"
    
    # Move GitHub AI configs
    if [[ -d "$ROOT_DIR/.github/chatmodes" ]]; then
        move_dir "$ROOT_DIR/.github/chatmodes" "$ROOT_DIR/.ai/copilot/chatmodes" "Moving chatmodes to .ai/copilot/"
    fi
    if [[ -d "$ROOT_DIR/.github/instructions" ]]; then
        move_dir "$ROOT_DIR/.github/instructions" "$ROOT_DIR/.ai/copilot/instructions" "Moving instructions to .ai/copilot/"
    fi
    
    # Create symlink for .cursorrules compatibility
    if [[ -f "$ROOT_DIR/.cursorrules" ]] && [[ -d "$ROOT_DIR/.ai/cursor" ]]; then
        if $DRY_RUN; then
            log DRY "Note: .cursorrules should be updated to reference .ai/cursor/rules/"
        fi
    fi
}

# =========================================
# PHASE 2: Consolidate Documentation
# =========================================
phase_2_documentation() {
    log PHASE "=== Phase 2: Consolidate Documentation ==="
    
    # Rename concepts to architecture
    move_dir "$ROOT_DIR/docs/concepts" "$ROOT_DIR/docs/architecture" "Renaming docs/concepts/ to docs/architecture/"
    
    # Move dev progress logs to archive (these are dev logs, not runtime)
    move_dir "$ROOT_DIR/docs/logs" "$ROOT_DIR/docs/archive/progress-logs" "Moving docs/logs/ to docs/archive/progress-logs/"
    
    # Create guides directory and merge how-to + tutorials
    if [[ -d "$ROOT_DIR/docs/how-to" ]]; then
        # Rename how-to to guides (it will become the base)
        move_dir "$ROOT_DIR/docs/how-to" "$ROOT_DIR/docs/guides" "Renaming docs/how-to/ to docs/guides/"
    fi
    
    if [[ -d "$ROOT_DIR/docs/tutorials" ]]; then
        move_dir "$ROOT_DIR/docs/tutorials" "$ROOT_DIR/docs/guides/tutorials" "Moving tutorials into guides/"
    fi
    
    # Consolidate development docs
    if [[ -d "$ROOT_DIR/docs/dev" ]]; then
        move_dir "$ROOT_DIR/docs/dev" "$ROOT_DIR/docs/guides/dev" "Moving docs/dev/ to docs/guides/dev/"
    fi
    if [[ -d "$ROOT_DIR/docs/development" ]]; then
        move_dir "$ROOT_DIR/docs/development" "$ROOT_DIR/docs/guides/development" "Moving docs/development/ to docs/guides/development/"
    fi
    
    # Move implementation to architecture
    if [[ -d "$ROOT_DIR/docs/implementation" ]]; then
        move_dir "$ROOT_DIR/docs/implementation" "$ROOT_DIR/docs/architecture/implementation" "Moving implementation/ to architecture/"
    fi
    
    # Move contributing to guides
    if [[ -d "$ROOT_DIR/docs/contributing" ]]; then
        move_dir "$ROOT_DIR/docs/contributing" "$ROOT_DIR/docs/guides/contributing" "Moving contributing/ to guides/"
    fi
    
    # Move known-issues to troubleshooting
    if [[ -d "$ROOT_DIR/docs/known-issues" ]]; then
        move_dir "$ROOT_DIR/docs/known-issues" "$ROOT_DIR/docs/troubleshooting/known-issues" "Moving known-issues/ to troubleshooting/"
    fi
    
    # Move indices to reference (if it's not empty)
    if [[ -d "$ROOT_DIR/docs/indices" ]]; then
        local count=$(find "$ROOT_DIR/docs/indices" -type f 2>/dev/null | wc -l)
        if [[ "$count" -gt 0 ]]; then
            move_dir "$ROOT_DIR/docs/indices" "$ROOT_DIR/docs/reference/indices" "Moving indices/ to reference/"
        fi
    fi
}

# =========================================
# PHASE 3: Consolidate External Dependencies
# =========================================
phase_3_external_deps() {
    log PHASE "=== Phase 3: Consolidate External Dependencies → vendor/ ==="
    
    if [[ -d "$ROOT_DIR/external" ]] || [[ -d "$ROOT_DIR/bindings" ]]; then
        ensure_dir "$ROOT_DIR/vendor"
        
        # Move external subdirs
        if [[ -d "$ROOT_DIR/external" ]]; then
            for subdir in "$ROOT_DIR/external"/*; do
                if [[ -d "$subdir" ]]; then
                    local name=$(basename "$subdir")
                    move_dir "$subdir" "$ROOT_DIR/vendor/$name" "Moving external/$name to vendor/"
                fi
            done
        fi
        
        # Move bindings subdirs
        if [[ -d "$ROOT_DIR/bindings" ]]; then
            for subdir in "$ROOT_DIR/bindings"/*; do
                if [[ -d "$subdir" ]]; then
                    local name=$(basename "$subdir")
                    move_dir "$subdir" "$ROOT_DIR/vendor/$name" "Moving bindings/$name to vendor/"
                fi
            done
        fi
    fi
}

# =========================================
# PHASE 4: Clean Up Root Level
# =========================================
phase_4_root_cleanup() {
    log PHASE "=== Phase 4: Clean Up Root Level ==="
    
    # Move orphaned root npm files to archive
    if [[ -f "$ROOT_DIR/package.json" ]] && [[ -d "$ROOT_DIR/node_modules" ]]; then
        # Check if this is actually orphaned (frontend has its own)
        if [[ -f "$ROOT_DIR/frontend/package.json" ]]; then
            ensure_dir "$ROOT_DIR/.local/archive/root-npm"
            move_dir "$ROOT_DIR/node_modules" "$ROOT_DIR/.local/archive/root-npm/node_modules" "Moving orphaned root node_modules to archive"
            move_dir "$ROOT_DIR/package.json" "$ROOT_DIR/.local/archive/root-npm/package.json" "Moving orphaned root package.json to archive"
            if [[ -f "$ROOT_DIR/package-lock.json" ]]; then
                move_dir "$ROOT_DIR/package-lock.json" "$ROOT_DIR/.local/archive/root-npm/package-lock.json" "Moving package-lock.json to archive"
            fi
        fi
    fi
    
    # Move legacy GitLab CI file
    if [[ -f "$ROOT_DIR/.gitlab-ci.yml.e2e" ]]; then
        move_dir "$ROOT_DIR/.gitlab-ci.yml.e2e" "$ROOT_DIR/.local/archive/.gitlab-ci.yml.e2e" "Moving legacy GitLab CI file to archive"
    fi
    
    # Move output suppression whitelist to ops config
    if [[ -f "$ROOT_DIR/.output-suppression-whitelist" ]]; then
        ensure_dir "$ROOT_DIR/ops/config"
        move_dir "$ROOT_DIR/.output-suppression-whitelist" "$ROOT_DIR/ops/config/output-suppression-whitelist" "Moving output-suppression-whitelist to ops/config/"
    fi
}

# =========================================
# PHASE 5: Consolidate Scripts
# =========================================
phase_5_scripts() {
    log PHASE "=== Phase 5: Consolidate Scripts → scripts/ ==="
    
    ensure_dir "$ROOT_DIR/scripts"
    
    # Move ops/scripts to scripts/ops (the largest collection)
    if [[ -d "$ROOT_DIR/ops/scripts" ]]; then
        move_dir "$ROOT_DIR/ops/scripts" "$ROOT_DIR/scripts/ops" "Moving ops/scripts/ to scripts/ops/"
    fi
    
    # Move backend/src/scripts to scripts/backend
    if [[ -d "$ROOT_DIR/backend/src/scripts" ]]; then
        move_dir "$ROOT_DIR/backend/src/scripts" "$ROOT_DIR/scripts/backend" "Moving backend/src/scripts/ to scripts/backend/"
    fi
    
    # Keep frontend/scripts where it is (frontend-specific build tooling)
    # But create a symlink for discoverability
    if [[ -d "$ROOT_DIR/frontend/scripts" ]] && [[ ! -L "$ROOT_DIR/scripts/frontend" ]]; then
        create_symlink "../frontend/scripts" "$ROOT_DIR/scripts/frontend" "Creating symlink scripts/frontend → ../frontend/scripts"
    fi
    
    # Move .local/archive/scripts to scripts/archive
    if [[ -d "$ROOT_DIR/.local/archive/scripts" ]]; then
        move_dir "$ROOT_DIR/.local/archive/scripts" "$ROOT_DIR/scripts/archive" "Moving .local/archive/scripts/ to scripts/archive/"
    fi
    
    # Create README for scripts directory
    if $DRY_RUN; then
        log DRY "Would create scripts/README.md"
    else
        if [[ ! -f "$ROOT_DIR/scripts/README.md" ]]; then
            cat > "$ROOT_DIR/scripts/README.md" << 'EOF'
# DSA-110 Scripts

Consolidated scripts directory for the DSA-110 continuum imaging pipeline.

## Structure

- `ops/` - Operational scripts (calibration, imaging, deployment, diagnostics)
- `backend/` - Backend utility scripts  
- `frontend/` → `../frontend/scripts/` - Frontend build/test scripts (symlink)
- `archive/` - Legacy/experimental scripts

## Usage

Most scripts require the `casa6` conda environment:

```bash
conda activate casa6
./scripts/ops/health_check.sh
```
EOF
            log OK "Created scripts/README.md"
        fi
    fi
}

# =========================================
# PHASE 6: Consolidate Config Files
# =========================================
phase_6_config_files() {
    log PHASE "=== Phase 6: Consolidate Config Files → config/ ==="
    
    ensure_dir "$ROOT_DIR/config"
    ensure_dir "$ROOT_DIR/config/linting"
    ensure_dir "$ROOT_DIR/config/hooks"
    ensure_dir "$ROOT_DIR/config/docker"
    ensure_dir "$ROOT_DIR/config/editor"
    
    # Move linting configs
    if [[ -f "$ROOT_DIR/.flake8" ]]; then
        move_dir "$ROOT_DIR/.flake8" "$ROOT_DIR/config/linting/.flake8" "Moving .flake8 to config/linting/"
        create_symlink "config/linting/.flake8" "$ROOT_DIR/.flake8" "Creating .flake8 symlink for tool compatibility"
    fi
    
    if [[ -f "$ROOT_DIR/.prettierrc" ]]; then
        move_dir "$ROOT_DIR/.prettierrc" "$ROOT_DIR/config/linting/.prettierrc" "Moving .prettierrc to config/linting/"
        create_symlink "config/linting/.prettierrc" "$ROOT_DIR/.prettierrc" "Creating .prettierrc symlink for tool compatibility"
    fi
    
    if [[ -f "$ROOT_DIR/.prettierignore" ]]; then
        move_dir "$ROOT_DIR/.prettierignore" "$ROOT_DIR/config/linting/.prettierignore" "Moving .prettierignore to config/linting/"
        create_symlink "config/linting/.prettierignore" "$ROOT_DIR/.prettierignore" "Creating .prettierignore symlink"
    fi
    
    # Move hooks configs
    if [[ -f "$ROOT_DIR/.pre-commit-config.yaml" ]]; then
        move_dir "$ROOT_DIR/.pre-commit-config.yaml" "$ROOT_DIR/config/hooks/.pre-commit-config.yaml" "Moving .pre-commit-config.yaml to config/hooks/"
        create_symlink "config/hooks/.pre-commit-config.yaml" "$ROOT_DIR/.pre-commit-config.yaml" "Creating .pre-commit-config.yaml symlink"
    fi
    
    if [[ -d "$ROOT_DIR/.husky" ]]; then
        move_dir "$ROOT_DIR/.husky" "$ROOT_DIR/config/hooks/husky" "Moving .husky to config/hooks/husky/"
        create_symlink "config/hooks/husky" "$ROOT_DIR/.husky" "Creating .husky symlink"
    fi
    
    if [[ -d "$ROOT_DIR/.githooks" ]]; then
        move_dir "$ROOT_DIR/.githooks" "$ROOT_DIR/config/hooks/githooks" "Moving .githooks to config/hooks/githooks/"
    fi
    
    # Move docker configs
    if [[ -f "$ROOT_DIR/docker-compose.yml" ]]; then
        move_dir "$ROOT_DIR/docker-compose.yml" "$ROOT_DIR/config/docker/docker-compose.yml" "Moving docker-compose.yml to config/docker/"
        create_symlink "config/docker/docker-compose.yml" "$ROOT_DIR/docker-compose.yml" "Creating docker-compose.yml symlink"
    fi
    
    if [[ -f "$ROOT_DIR/Dockerfile.copilot" ]]; then
        move_dir "$ROOT_DIR/Dockerfile.copilot" "$ROOT_DIR/config/docker/Dockerfile.copilot" "Moving Dockerfile.copilot to config/docker/"
    fi
    
    # Move editor configs
    if [[ -f "$ROOT_DIR/.editorconfig" ]]; then
        move_dir "$ROOT_DIR/.editorconfig" "$ROOT_DIR/config/editor/.editorconfig" "Moving .editorconfig to config/editor/"
        create_symlink "config/editor/.editorconfig" "$ROOT_DIR/.editorconfig" "Creating .editorconfig symlink"
    fi
    
    if [[ -f "$ROOT_DIR/.nvmrc" ]]; then
        move_dir "$ROOT_DIR/.nvmrc" "$ROOT_DIR/config/editor/.nvmrc" "Moving .nvmrc to config/editor/"
        create_symlink "config/editor/.nvmrc" "$ROOT_DIR/.nvmrc" "Creating .nvmrc symlink"
    fi
    
    # Move environment pins
    if [[ -f "$ROOT_DIR/environment-pins.txt" ]]; then
        move_dir "$ROOT_DIR/environment-pins.txt" "$ROOT_DIR/config/environment-pins.txt" "Moving environment-pins.txt to config/"
    fi
    
    # Create README for config directory
    if $DRY_RUN; then
        log DRY "Would create config/README.md"
    else
        if [[ ! -f "$ROOT_DIR/config/README.md" ]]; then
            cat > "$ROOT_DIR/config/README.md" << 'EOF'
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
EOF
            log OK "Created config/README.md"
        fi
    fi
}

# =========================================
# PHASE 7: Consolidate State Directories
# =========================================
phase_7_state_dirs() {
    log PHASE "=== Phase 7: Consolidate State Directories → state/ ==="
    
    # The main /state directory (6.8 GB) is the canonical location
    # We'll consolidate other state dirs into it
    
    ensure_dir "$ROOT_DIR/state/databases"
    ensure_dir "$ROOT_DIR/state/frontend"
    
    # Move frontend/state to state/frontend
    if [[ -d "$ROOT_DIR/frontend/state" ]]; then
        # Check if it has content
        local count=$(find "$ROOT_DIR/frontend/state" -type f 2>/dev/null | wc -l)
        if [[ "$count" -gt 0 ]]; then
            move_dir "$ROOT_DIR/frontend/state" "$ROOT_DIR/state/frontend" "Moving frontend/state/ to state/frontend/"
            # Create symlink back for frontend compatibility
            create_symlink "../state/frontend" "$ROOT_DIR/frontend/state" "Creating frontend/state symlink"
        fi
    fi
    
    # Move backend/state to state/backend (if it has content)
    if [[ -d "$ROOT_DIR/backend/state" ]]; then
        local count=$(find "$ROOT_DIR/backend/state" -type f 2>/dev/null | wc -l)
        if [[ "$count" -gt 0 ]]; then
            move_dir "$ROOT_DIR/backend/state" "$ROOT_DIR/state/backend" "Moving backend/state/ to state/backend/"
        fi
    fi
    
    # Move backend/src/state to state/backend-src (if it exists and has content)
    if [[ -d "$ROOT_DIR/backend/src/state" ]]; then
        local count=$(find "$ROOT_DIR/backend/src/state" -type f 2>/dev/null | wc -l)
        if [[ "$count" -gt 0 ]]; then
            move_dir "$ROOT_DIR/backend/src/state" "$ROOT_DIR/state/backend-src" "Moving backend/src/state/ to state/backend-src/"
        fi
    fi
    
    # Move .local/state_src_orphaned to state/archive/orphaned
    if [[ -d "$ROOT_DIR/.local/state_src_orphaned" ]]; then
        move_dir "$ROOT_DIR/.local/state_src_orphaned" "$ROOT_DIR/state/archive/orphaned" "Moving orphaned state to state/archive/orphaned/"
    fi
    
    # docs/state contains documentation about state management, not actual state
    # Rename it to be clearer
    if [[ -d "$ROOT_DIR/docs/state" ]]; then
        move_dir "$ROOT_DIR/docs/state" "$ROOT_DIR/docs/reference/state-management" "Moving docs/state/ to docs/reference/state-management/"
    fi
}

# =========================================
# PHASE 8: Clean Up Hidden Directories
# =========================================
phase_8_hidden_dirs() {
    log PHASE "=== Phase 8: Clean Up Hidden Directories ==="
    
    # Move .watch to .local if not actively used
    if [[ -d "$ROOT_DIR/.watch" ]]; then
        local count=$(find "$ROOT_DIR/.watch" -type f 2>/dev/null | wc -l)
        if [[ "$count" -eq 0 ]]; then
            log INFO ".watch is empty, will be removed in cleanup phase"
        else
            move_dir "$ROOT_DIR/.watch" "$ROOT_DIR/.local/watch" "Moving .watch to .local/watch/"
        fi
    fi
    
    # Consolidate .githooks into .husky if both exist (or into config/hooks)
    # Already handled in phase 6
    
    # Note about cache directories (don't move, just document)
    log INFO "Note: Cache directories (.mypy_cache, .pytest_cache, .ruff_cache) are left in place"
    log INFO "      They are gitignored and regenerated automatically"
    
    # Ensure common caches are in .gitignore
    if $DRY_RUN; then
        log DRY "Would verify .gitignore includes cache directories"
    else
        # Check if .gitignore exists and has cache patterns
        if [[ -f "$ROOT_DIR/.gitignore" ]]; then
            local missing_patterns=""
            for pattern in ".mypy_cache/" ".pytest_cache/" ".ruff_cache/" "__pycache__/"; do
                if ! grep -q "^${pattern}$" "$ROOT_DIR/.gitignore" 2>/dev/null; then
                    missing_patterns="$missing_patterns $pattern"
                fi
            done
            if [[ -n "$missing_patterns" ]]; then
                log WARN "Consider adding to .gitignore:$missing_patterns"
            fi
        fi
    fi
}

# =========================================
# PHASE 9: Restructure Ops Directory
# =========================================
phase_9_ops_restructure() {
    log PHASE "=== Phase 9: Restructure Ops Directory ==="
    
    # ops/scripts was moved in phase 5, so ops should now be pure infrastructure
    # Move ops/docs to main docs if it exists
    if [[ -d "$ROOT_DIR/ops/docs" ]]; then
        move_dir "$ROOT_DIR/ops/docs" "$ROOT_DIR/docs/operations/ops-docs" "Moving ops/docs/ to docs/operations/ops-docs/"
    fi
    
    # Consolidate ops structure
    # - docker/ stays (Dockerfiles, compose)
    # - systemd/ stays (service definitions)
    # - logrotate.d/ stays
    # - env/ stays (environment configs)
    # - pipeline/ could move to config/pipeline
    if [[ -d "$ROOT_DIR/ops/pipeline" ]]; then
        move_dir "$ROOT_DIR/ops/pipeline" "$ROOT_DIR/config/pipeline" "Moving ops/pipeline/ to config/pipeline/"
    fi
    
    # simulation could move to a more appropriate location
    if [[ -d "$ROOT_DIR/ops/simulation" ]]; then
        move_dir "$ROOT_DIR/ops/simulation" "$ROOT_DIR/config/simulation" "Moving ops/simulation/ to config/simulation/"
    fi
    
    log INFO "Ops directory now contains: docker, systemd, logrotate.d, env"
}

# =========================================
# PHASE 10: Create Products Symlinks
# =========================================
phase_10_products_symlinks() {
    log PHASE "=== Phase 10: Create Products Symlinks (optional) ==="
    
    # The products directory has empty subdirectories that could be symlinks
    # to the actual storage locations on /stage
    
    local stage_dir="/stage/dsa110-contimg"
    
    if [[ -d "$stage_dir" ]]; then
        log INFO "Found stage directory: $stage_dir"
        
        # Create symlinks for each product type if stage has the directory
        for product_type in caltables images ms mosaics catalogs; do
            if [[ -d "$stage_dir/$product_type" ]] && [[ -d "$ROOT_DIR/products/$product_type" ]]; then
                # Only create symlink if products dir is empty
                local count=$(find "$ROOT_DIR/products/$product_type" -type f 2>/dev/null | wc -l)
                if [[ "$count" -eq 0 ]]; then
                    if $DRY_RUN; then
                        log DRY "Would remove empty $ROOT_DIR/products/$product_type"
                        log DRY "Would create symlink products/$product_type → $stage_dir/$product_type"
                    else
                        rmdir "$ROOT_DIR/products/$product_type" 2>/dev/null || true
                        create_symlink "$stage_dir/$product_type" "$ROOT_DIR/products/$product_type" "Linking products/$product_type to stage"
                    fi
                fi
            fi
        done
    else
        log INFO "Stage directory not found ($stage_dir), skipping product symlinks"
        log INFO "Products directory will retain empty subdirectories for future use"
    fi
}

# =========================================
# PHASE 11: Remove Empty Directories
# =========================================
phase_11_empty_dirs() {
    log PHASE "=== Phase 11: Remove Empty Directories ==="
    
    # Remove empty dirs in specific locations (after moves)
    remove_empty_dirs "$ROOT_DIR/products"
    remove_empty_dirs "$ROOT_DIR/external"
    remove_empty_dirs "$ROOT_DIR/bindings"
    remove_empty_dirs "$ROOT_DIR/docs"
    remove_empty_dirs "$ROOT_DIR/ops"
    remove_empty_dirs "$ROOT_DIR/.local"
    remove_empty_dirs "$ROOT_DIR/backend/src"
    remove_empty_dirs "$ROOT_DIR/.watch"
}

# =========================================
# PHASE 12: Create Compatibility Symlinks
# =========================================
phase_12_symlinks() {
    log PHASE "=== Phase 12: Create Compatibility Symlinks ==="
    
    # Create .cursor symlink if it was moved
    if [[ -d "$ROOT_DIR/.ai/cursor" ]] && [[ ! -e "$ROOT_DIR/.cursor" ]]; then
        create_symlink ".ai/cursor" "$ROOT_DIR/.cursor" "Creating .cursor compatibility symlink"
    fi
    
    # Create ops/scripts symlink to new location
    if [[ -d "$ROOT_DIR/scripts/ops" ]] && [[ ! -e "$ROOT_DIR/ops/scripts" ]]; then
        create_symlink "../scripts/ops" "$ROOT_DIR/ops/scripts" "Creating ops/scripts compatibility symlink"
    fi
    
    # Verify all critical symlinks exist
    log INFO "Verifying critical paths..."
    local critical_paths=(
        ".github/copilot-instructions.md"
        "backend/src/dsa110_contimg"
        "frontend/src"
        "docs/SYSTEM_CONTEXT.md"
    )
    
    for path in "${critical_paths[@]}"; do
        if [[ -e "$ROOT_DIR/$path" ]]; then
            log OK "✓ $path exists"
        else
            log WARN "✗ $path missing!"
        fi
    done
}

# =========================================
# Main reorganization logic
# =========================================
main() {
    log INFO "=========================================="
    log INFO "DSA-110 Directory Reorganization"
    log INFO "=========================================="
    log INFO "Root: $ROOT_DIR"
    log INFO "Mode: $(if $DRY_RUN; then echo 'DRY-RUN (no changes will be made)'; else echo 'EXECUTE'; fi)"
    if [[ -n "$PHASE_FILTER" ]]; then
        log INFO "Phase: $PHASE_FILTER only"
    fi
    log INFO ""
    
    # Validate root directory
    if [[ ! -d "$ROOT_DIR" ]]; then
        log ERROR "Root directory does not exist: $ROOT_DIR"
        exit 1
    fi
    
    cd "$ROOT_DIR"
    
    # Initialize rollback file
    if ! $DRY_RUN; then
        mkdir -p "$(dirname "$ROLLBACK_FILE")"
        mkdir -p "$(dirname "$LOG_FILE")"
        echo "#!/usr/bin/env bash" > "$ROLLBACK_FILE"
        echo "# Rollback script generated on $(date)" >> "$ROLLBACK_FILE"
        echo "# Run this script to undo the reorganization" >> "$ROLLBACK_FILE"
        echo "set -euo pipefail" >> "$ROLLBACK_FILE"
        echo "cd '$ROOT_DIR'" >> "$ROLLBACK_FILE"
        echo "" >> "$ROLLBACK_FILE"
    else
        mkdir -p "$(dirname "$ROLLBACK_FILE")" 2>/dev/null || true
        echo "# Preview of rollback commands" > "${ROLLBACK_FILE}.preview" 2>/dev/null || true
    fi
    
    # Run phases
    should_run_phase 1 && phase_1_ai_configs
    should_run_phase 2 && phase_2_documentation
    should_run_phase 3 && phase_3_external_deps
    should_run_phase 4 && phase_4_root_cleanup
    should_run_phase 5 && phase_5_scripts
    should_run_phase 6 && phase_6_config_files
    should_run_phase 7 && phase_7_state_dirs
    should_run_phase 8 && phase_8_hidden_dirs
    should_run_phase 9 && phase_9_ops_restructure
    should_run_phase 10 && phase_10_products_symlinks
    should_run_phase 11 && phase_11_empty_dirs
    should_run_phase 12 && phase_12_symlinks
    
    # =========================================
    # Summary
    # =========================================
    log INFO ""
    log INFO "=========================================="
    log INFO "Reorganization $(if $DRY_RUN; then echo 'Preview'; else echo 'Complete'; fi)"
    log INFO "=========================================="
    
    if $DRY_RUN; then
        log INFO ""
        log INFO "This was a DRY RUN. No changes were made."
        log INFO "To execute, run: $0 --execute"
        log INFO ""
        log INFO "To run a specific phase: $0 --phase N --dry-run"
        log INFO ""
        if [[ -f "${ROLLBACK_FILE}.preview" ]]; then
            log INFO "Preview of rollback commands saved to: ${ROLLBACK_FILE}.preview"
        fi
    else
        log INFO ""
        log INFO "Rollback script saved to: $ROLLBACK_FILE"
        log INFO "Log file saved to: $LOG_FILE"
        log INFO ""
        log INFO "To undo these changes, run: bash $ROLLBACK_FILE"
        log INFO ""
        log INFO "IMPORTANT: After reorganization, update:"
        log INFO "  1. mkdocs.yml - navigation paths"
        log INFO "  2. .github/copilot-instructions.md - directory references"
        log INFO "  3. CI/CD workflows - any hardcoded paths"
        chmod +x "$ROLLBACK_FILE"
    fi
}

# Handle rollback mode
if $ROLLBACK; then
    # Find the most recent rollback file
    LATEST_ROLLBACK=$(ls -t "$ROOT_DIR/.local/reorganize_rollback_"*.sh 2>/dev/null | head -1)
    
    if [[ -z "$LATEST_ROLLBACK" ]]; then
        log ERROR "No rollback script found in $ROOT_DIR/.local/"
        exit 1
    fi
    
    log INFO "Running rollback script: $LATEST_ROLLBACK"
    bash "$LATEST_ROLLBACK"
    log OK "Rollback complete"
    exit 0
fi

# Run main
main
