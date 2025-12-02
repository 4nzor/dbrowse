.PHONY: help install install-dev run test clean test-db format lint type-check setup venv

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
TEST_DB := test_database.db

help: ## Show this help message
	@echo "dbrowse - Makefile commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

setup: venv install ## Set up development environment (venv + install dependencies)

venv: ## Create virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created!"; \
	else \
		echo "Virtual environment already exists"; \
	fi

install: venv ## Install dependencies
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Dependencies installed!"

install-dev: install ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install pytest black flake8 mypy
	@echo "Development dependencies installed!"

run: ## Run dbrowse application
	@echo "Starting dbrowse..."
	$(PYTHON_VENV) main.py

test-db: ## Create test database for screenshots
	@echo "Creating test database..."
	$(PYTHON_VENV) scripts/create_test_db.py

clean: ## Clean up generated files
	@echo "Cleaning up..."
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf *.pyo
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf *.egg-info/
	rm -rf dist/
	rm -rf build/
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

clean-db: ## Remove test database
	@echo "Removing test database..."
	rm -f $(TEST_DB)
	@echo "Test database removed!"

clean-all: clean clean-db ## Clean everything including test database

format: ## Format code with black
	@echo "Formatting code with black..."
	$(PYTHON_VENV) -m black --line-length 100 main.py database.py ui.py utils.py scripts/*.py
	@echo "Code formatted!"

lint: ## Lint code with flake8
	@echo "Linting code with flake8..."
	$(PYTHON_VENV) -m flake8 --max-line-length=100 --ignore=E501,W503 main.py database.py ui.py utils.py
	@echo "Linting complete!"

type-check: ## Type check with mypy
	@echo "Type checking with mypy..."
	$(PYTHON_VENV) -m mypy --ignore-missing-imports main.py database.py ui.py utils.py || true
	@echo "Type checking complete!"

check: format lint type-check ## Run all checks (format, lint, type-check)

test: ## Run tests (placeholder for future tests)
	@echo "Running tests..."
	@echo "No tests yet. Add tests to run them here."
	# $(PYTHON_VENV) -m pytest tests/

build: ## Build package for distribution
	@echo "Building package..."
	$(PYTHON_VENV) -m pip install build
	$(PYTHON_VENV) -m build
	@echo "Package built! Check dist/ directory."

install-package: ## Install package in development mode (makes 'dbrowse' command available)
	@echo "Installing package in development mode..."
	$(PIP) install -e .
	@echo "Package installed! You can now run 'dbrowse' or 'dbrowser' command."

requirements: ## Update requirements.txt from current environment
	@echo "Updating requirements.txt..."
	$(PIP) freeze > requirements.txt
	@echo "Requirements updated!"

# Development workflow
dev: setup test-db ## Set up development environment and create test DB
	@echo "Development environment ready!"
	@echo "Run 'make run' to start dbrowse"

# Quick start for new contributors
quickstart: setup test-db ## Quick start: setup + test DB
	@echo ""
	@echo "✅ Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make run' to start dbrowse"
	@echo "  2. Add test database connection (sqlite://test_database.db)"
	@echo "  3. Start developing!"
	@echo ""

release: ## Create GitHub release (usage: make release VERSION=0.1.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required"; \
		echo "Usage: make release VERSION=0.1.0"; \
		echo "See .local-docs/QUICK_RELEASE.md for detailed instructions"; \
		exit 1; \
	fi
	@./scripts/create_release.sh $(VERSION)

sha256: ## Get SHA256 for release (usage: make sha256 VERSION=0.1.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required"; \
		echo "Usage: make sha256 VERSION=0.1.0"; \
		exit 1; \
	fi
	@./scripts/get_sha256.sh $(VERSION)

setup-tap: ## Set up Homebrew tap (creates homebrew-dbrowse repo and formula)
	@./scripts/setup_homebrew_tap.sh

