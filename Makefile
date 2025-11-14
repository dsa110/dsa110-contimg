# Makefile targets for test organization validation

.PHONY: test-validate test-org-install test-org-check test-pytest-validate check-env setup-dev auto-fix check-code-quality
 .PHONY: doc-audit

# Validate test organization
test-validate:
	@echo "Validating test organization..."
	@/opt/miniforge/envs/casa6/bin/python scripts/validate-test-organization.py

# Validate pytest usage patterns
test-pytest-validate:
	@echo "Validating pytest usage patterns..."
	@./scripts/validate-pytest-usage.sh

# Install pre-commit hook for test organization
test-org-install:
	@./scripts/test-organization-enforcer.sh install

# Check test organization
test-org-check:
	@./scripts/test-organization-enforcer.sh check

# Check development environment
check-env:
	@./scripts/check-environment.sh

# Setup development environment
setup-dev:
	@./scripts/setup-dev.sh

# Auto-fix common gotchas
auto-fix:
	@./scripts/auto-fix-gotchas.sh

# Check code quality
check-code-quality:
	@./scripts/check-code-quality.sh

# Run documentation audit to verify endpoints and links
doc-audit:
	@echo "Running documentation audit..."
	@python3 scripts/doc_audit.py
