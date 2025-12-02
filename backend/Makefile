# DSA-110 Continuum Imaging Pipeline - Development Commands
# Usage: make <target>

.PHONY: help test test-unit test-contract test-fast test-parallel lint typecheck clean

# Default target
help:
	@echo "DSA-110 Contimg Development Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests (unit + contract)"
	@echo "  make test-unit     - Run unit tests only (~55s)"
	@echo "  make test-contract - Run contract tests only (~45s)"
	@echo "  make test-fast     - Run fast unit tests only (~40s)"
	@echo "  make test-parallel - Run tests in parallel (requires pytest-xdist)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run flake8 linter"
	@echo "  make typecheck     - Run mypy type checker"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Remove cache files"
	@echo "  make install-dev   - Install dev dependencies"

# Testing targets
test-unit:
	python -m pytest tests/unit/ -q --tb=short

test-contract:
	python -m pytest tests/contract/ -q --tb=short

test-fast:
	python -m pytest tests/unit/test_*.py -q --tb=short

test-parallel:
	python -m pytest tests/unit/ -n 4 -q --tb=short

test: test-unit test-contract

# Code quality
lint:
	flake8 src/dsa110_contimg --max-line-length=100 --ignore=E501,W503

typecheck:
	mypy src/dsa110_contimg --ignore-missing-imports

# Utilities
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

install-dev:
	pip install -e ".[dev]"
