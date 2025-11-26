# Makefile targets for test organization validation

# Python interpreter - can be overridden via environment variable
CASA6_PYTHON ?= /opt/miniforge/envs/casa6/bin/python

.PHONY: test-validate test-org-install test-org-check test-pytest-validate check-env setup-dev auto-fix check-code-quality
.PHONY: doc-audit validate-python-version test-python-guards

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
