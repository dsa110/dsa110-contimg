#!/usr/bin/env bash
set -euo pipefail

# Impacted tests runner for DSA-110 Continuum Pipeline
#
# Detects changed files and runs only the most relevant, fast tests.
#
# Usage:
#   bash scripts/test-impacted.sh [BASE_REF]
#   BASE_REF environment variable is also respected; default: HEAD~1
#
# Behavior:
# - Prefers CASA6 Python if available, otherwise falls back to system python.
# - Excludes slow, integration, and casa-marked tests by default.
# - Maps changes in src/ to related tests using ripgrep if present, else grep.

CASA6_PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
CASA6_PYTHON="${CASA6_PYTHON_BIN} -W ignore::DeprecationWarning"
if [[ -x "$CASA6_PYTHON_BIN" ]]; then
  PY="$CASA6_PYTHON"
else
  echo "WARNING: CASA6 Python not found at $CASA6_PYTHON_BIN; using system python." >&2
  PY="$(command -v python || command -v python3 || echo python)"
fi

BASE_REF="${1:-${BASE_REF:-HEAD~1}}"

has_cmd() { command -v "$1" >/dev/null 2>&1; }
FIND_L() {
  # Print files matching pattern under path
  local pattern="$1"; shift; local path="$1"; shift || true
  if has_cmd rg; then
    rg -l -n -S "$pattern" "$path" || true
  else
    grep -RIl --line-number --binary-files=without-match -E "$pattern" "$path" || true
  fi
}

# Ensure we can compute changed files
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository. Running fast unit tests as fallback..." >&2
  PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}" "$PY" -m pytest tests/unit -q -x --maxfail=1 -m "unit and not slow and not integration and not casa"
  exit $?
fi

CHANGED_FILES="$(git diff --name-only "$BASE_REF" || true)"

# If nothing changed, run fast unit sweep
if [[ -z "$CHANGED_FILES" ]]; then
  echo "No changed files since $BASE_REF. Running fast unit tests..."
  PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}" "$PY" -m pytest tests/unit -q -x --maxfail=1 -m "unit and not slow and not integration and not casa"
  exit $?
fi

echo "Changed files since $BASE_REF:" >&2
echo "$CHANGED_FILES" | sed 's/^/  - /' >&2

declare -a TEST_FILES

# If changed tests, run them directly
while IFS= read -r f; do
  if [[ "$f" == tests/* && "$f" == *.py ]]; then
    TEST_FILES+=("$f")
  fi
done <<< "$CHANGED_FILES"

# Map src changes to tests
while IFS= read -r f; do
  [[ "$f" != src/dsa110_contimg/* ]] && continue
  # Determine top-level package area after dsa110_contimg/
  rel="${f#src/dsa110_contimg/}"
  area="${rel%%/*}"
  module_path="${rel%.*}"
  module_dotted="dsa110_contimg.${module_path//\//.}"

  case "$area" in
    pipeline)
      # Orchestrator/config related tests
      TEST_FILES+=(tests/integration/test_orchestrator.py)
      TEST_FILES+=(tests/test_pipeline.py)
      ;;
    imaging)
      # Mocked imaging tests
      map=$(FIND_L "dsa110_contimg\\.imaging" tests)
      [[ -n "$map" ]] && TEST_FILES+=($map)
      ;;
    calibration)
      map=$(FIND_L "dsa110_contimg\\.calibration" tests)
      [[ -n "$map" ]] && TEST_FILES+=($map)
      ;;
    conversion)
      map=$(FIND_L "dsa110_contimg\\.conversion" tests)
      [[ -n "$map" ]] && TEST_FILES+=($map)
      ;;
    qa)
      TEST_FILES+=(tests/test_html_reports_simple.py tests/test_validation_plots.py)
      map=$(FIND_L "dsa110_contimg\\.qa" tests)
      [[ -n "$map" ]] && TEST_FILES+=($map)
      ;;
    catalog)
      TEST_FILES+=(tests/unit/test_catalog_validation.py)
      map=$(FIND_L "dsa110_contimg\\.catalog" tests)
      [[ -n "$map" ]] && TEST_FILES+=($map)
      ;;
    *)
      # Generic mapping by dotted module
      map=$(FIND_L "$module_dotted" tests)
      [[ -n "$map" ]] && TEST_FILES+=($map)
      ;;
  esac
done <<< "$CHANGED_FILES"

# De-duplicate and filter existing files
uniq_tests=$(printf "%s\n" "${TEST_FILES[@]:-}" | awk 'NF' | sort -u)

if [[ -z "$uniq_tests" ]]; then
  echo "No specific impacted tests found. Running fast unit tests..." >&2
  PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}" "$PY" -m pytest tests/unit -q -x --maxfail=1 -m "unit and not slow and not integration and not casa"
  exit $?
fi

echo "Running impacted tests:" >&2
echo "$uniq_tests" | sed 's/^/  - /' >&2

count=$(printf "%s\n" "$uniq_tests" | wc -l | awk '{print $1}')
if [ "$count" -gt 12 ]; then
  echo "Too many impacted tests ($count). Running smoke suite instead..." >&2
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLBACKEND=Agg \
  PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}" "$PY" -m pytest -q -x --maxfail=1 \
    tests/test_pipeline.py tests/unit/test_cli_calibration_args.py
else
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLBACKEND=Agg \
  PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}" "$PY" -m pytest -q -x --maxfail=1 -m "not slow and not integration and not casa" $uniq_tests
fi
