# Makefile targets for test organization validation

# Python interpreter - can be overridden via environment variable
CASA6_PYTHON ?= /opt/miniforge/envs/casa6/bin/python
BENCHMARK_DIR := benchmarks

.PHONY: test-validate test-org-install test-org-check test-pytest-validate check-env setup-dev auto-fix check-code-quality
.PHONY: doc-audit validate-python-version test-python-guards
.PHONY: bench bench-quick bench-report bench-check bench-info bench-compare bench-preview bench-calibration bench-conversion

# ============================================================================
# BENCHMARKING TARGETS
# ============================================================================
# Run performance benchmarks using airspeed-velocity (asv)
# See docs/guides/benchmarking.md for detailed documentation

# Quick benchmark check (~5-15 minutes, single iteration)
bench-quick:
	@echo "Running quick benchmark check..."
	@cd $(BENCHMARK_DIR) && asv run --quick --python=same --set-commit-hash=$$(git rev-parse HEAD)

# Full benchmark suite with statistics (~30-60 minutes)
bench:
	@echo "Running full benchmark suite..."
	@cd $(BENCHMARK_DIR) && asv run --python=same --set-commit-hash=$$(git rev-parse HEAD)

# Run only calibration benchmarks
bench-calibration:
	@echo "Running calibration benchmarks..."
	@cd $(BENCHMARK_DIR) && asv run --python=same --bench "Calibration" --set-commit-hash=$$(git rev-parse HEAD)

# Run only conversion benchmarks
bench-conversion:
	@echo "Running conversion benchmarks..."
	@cd $(BENCHMARK_DIR) && asv run --python=same --bench "Conversion" --set-commit-hash=$$(git rev-parse HEAD)

# Generate HTML benchmark report
bench-report:
	@echo "Generating benchmark HTML report..."
	@cd $(BENCHMARK_DIR) && asv publish && echo "Report: $(BENCHMARK_DIR)/.asv/html/index.html"

# Open benchmark report in browser
bench-preview:
	@echo "Opening benchmark report in browser..."
	@cd $(BENCHMARK_DIR) && asv preview

# Verify benchmark configuration
bench-check:
	@echo "Checking benchmark configuration..."
	@cd $(BENCHMARK_DIR) && asv check

# Show benchmark environment info
bench-info:
	@echo "Benchmark environment:"
	@echo "  Directory: $(BENCHMARK_DIR)"
	@echo "  Python: $(CASA6_PYTHON)"
	@echo "  Commit: $$(git rev-parse --short HEAD)"
	@echo ""
	@echo "Benchmark files:"
	@ls -1 $(BENCHMARK_DIR)/bench_*.py 2>/dev/null || echo "  (none found)"

# Compare benchmarks between commits (usage: make bench-compare BASE=HEAD~1 TARGET=HEAD)
BASE ?= HEAD~1
TARGET ?= HEAD
bench-compare:
	@echo "Comparing $(BASE) → $(TARGET)..."
	@cd $(BENCHMARK_DIR) && asv continuous $(BASE) $(TARGET) --factor 1.1

# ============================================================================
# TEST ORGANIZATION TARGETS
# ============================================================================

# Validate test organization
test-validate:
	@echo "Validating test organization..."
	@$(CASA6_PYTHON) scripts/ops/quality/validate-test-organization.py

# Validate pytest usage patterns
test-pytest-validate:
	@echo "Validating pytest usage patterns..."
	@./scripts/ops/quality/validate-pytest-usage.sh

# Install pre-commit hook for test organization
test-org-install:
	@./scripts/ops/tests/test-organization-enforcer.sh install

# Check test organization
test-org-check:
	@./scripts/ops/tests/test-organization-enforcer.sh check

# Check development environment
check-env:
	@./scripts/ops/quality/check-environment.sh

# Setup development environment
setup-dev:
	@./scripts/ops/dev/setup-dev.sh

# Auto-fix common gotchas
auto-fix:
	@./scripts/ops/quality/auto-fix-gotchas.sh

# Check code quality
check-code-quality:
	@./scripts/ops/quality/check-code-quality.sh

# Run documentation audit to verify endpoints and links
doc-audit:
	@echo "Running documentation audit..."
	@$(CASA6_PYTHON) scripts/ops/utils/doc_audit.py

# Validate Python version usage (prevents use of Python 2.7 or 3.6)
validate-python-version:
	@echo "Validating Python version usage..."
	@./scripts/ops/validate-python-version.sh

# Test Python version guards
test-python-guards:
	@echo "Testing Python version guards..."
	@./scripts/ops/test-python-guards.sh
