# Makefile for Varydian Financial Reporting System Tests
# Provides convenient commands for running tests and managing test environment

.PHONY: help test test-unit test-rbac test-ui test-api test-formula test-responsive test-all clean install-deps lint

# Default target
help:
	@echo "Varydian Financial Reporting System - Test Suite"
	@echo ""
	@echo "Available commands:"
	@echo "  help          - Show this help message"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-rbac      - Run RBAC permission tests"
	@echo "  test-ui       - Run UI integration tests"
	@echo "  test-api       - Run API endpoint tests"
	@echo "  test-formula  - Run formula transparency tests"
	@echo "  test-responsive- Run responsive design tests"
	@echo "  test-all      - Run complete test suite"
	@echo "  clean         - Clean test artifacts"
	@echo "  install-deps  - Install test dependencies"
	@echo "  lint          - Run code linting"

# Install dependencies
install-deps:
	@echo "Installing test dependencies..."
	pip install -r tests/requirements.txt
	@echo "Dependencies installed successfully!"

# Run all tests
test-all:
	@echo "Running complete test suite..."
	@echo "Make sure Flask app is running on localhost:5000"
	python tests/run_all_tests.py

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	python tests/test_formula_transparency.py

# Run RBAC tests
test-rbac:
	@echo "Running RBAC permission tests..."
	python tests/test_rbac_permissions.py

# Run UI tests
test-ui:
	@echo "Running UI integration tests..."
	@echo "Make sure Flask app is running and ChromeDriver is available"
	python tests/test_ui_integration.py

# Run API tests
test-api:
	@echo "Running API endpoint tests..."
	python tests/test_api_endpoints.py

# Run formula tests
test-formula:
	@echo "Running formula transparency tests..."
	python tests/test_formula_transparency.py

# Run responsive tests
test-responsive:
	@echo "Running responsive design tests..."
	python tests/test_responsive_design.py

# Run formula modal tests
test-formula-modal:
	@echo "Running formula modal functionality tests..."
	python tests/test_formula_modal_functionality.py

# Generic test command
test: test-all

# Clean test artifacts
clean:
	@echo "Cleaning test artifacts..."
	find tests/ -name "*.pyc" -delete
	find tests/ -name "__pycache__" -type d -exec rm -rf {} +
	find tests/ -name ".coverage" -delete
	find tests/ -name "htmlcov" -type d -exec rm -rf {} +
	find tests/ -name "*.log" -delete
	find tests/ -name "screenshots" -type d -exec rm -rf {} +
	rm -rf tests/.pytest_cache
	@echo "Clean completed!"

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	coverage run --source=. -m pytest tests/ || coverage run --source=. tests/run_all_tests.py
	coverage report
	coverage html

# Lint code
lint:
	@echo "Running code linting..."
	flake8 tests/ --max-line-length=100 --ignore=E501,W503
	pylint tests/ --disable=C0114,C0115

# Check code quality
quality:
	@echo "Running code quality checks..."
	black --check tests/
	isort --check-only tests/
	mypy tests/ --ignore-missing-imports

# Start test environment
start-env:
	@echo "Starting test environment..."
	@echo "Starting Flask app in background..."
	python run.py &
	@echo "Waiting for app to start..."
	sleep 5
	@echo "Test environment ready!"

# Stop test environment
stop-env:
	@echo "Stopping test environment..."
	pkill -f "python run.py"
	@echo "Test environment stopped!"

# Development test command (watch for changes)
dev-test:
	@echo "Running tests in watch mode..."
	watchdog --patterns="tests/*.py" --recursive --command="make test-unit"

# Continuous integration command
ci-test:
	@echo "Running CI tests..."
	coverage run --source=. tests/run_all_tests.py
	coverage xml
	coverage report --fail-under=80

# Performance tests
test-performance:
	@echo "Running performance tests..."
	python -m pytest tests/ --benchmark-only

# Security tests
test-security:
	@echo "Running security tests..."
	bandit -r tests/
	safety check

# Documentation tests
test-docs:
	@echo "Running documentation tests..."
	doctest tests/

# Parallel tests
test-parallel:
	@echo "Running tests in parallel..."
	python -m pytest tests/ -n auto

# Quick test (skip slow tests)
test-quick:
	@echo "Running quick tests (excluding slow ones)..."
	python -m pytest tests/ -m "not slow"

# Full test suite (including slow tests)
test-full:
	@echo "Running full test suite..."
	python -m pytest tests/ -v

# Generate test report
report:
	@echo "Generating test report..."
	python tests/run_all_tests.py > test-report.txt
	@echo "Test report saved to test-report.txt"
