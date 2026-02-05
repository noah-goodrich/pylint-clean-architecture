.PHONY: handshake test test-fast test-slow test-all
handshake:
	@echo "=== STELLAR PROTOCOL HANDSHAKE (Augmented) ==="
	@echo "1. READING REQUIREMENTS..."
	@ls .agent/*.md 2>/dev/null | grep -v "_" || (echo "ERROR: Files in .agent/ must use dashes, not underscores!" && exit 1)
	@echo "   [OK] .agent/ files verified."
	@echo "2. INTERPRETER AUDIT:"
	@python3 -c "import sys; print(f'   [INFO] StdLib Modules: {len(sys.stdlib_module_names)}');"
	@python3 -c "import sysconfig; print(f'   [INFO] StdLib Path: {sysconfig.get_path(\"stdlib\")}')"
	@echo "3. STUB AUDIT:"
	@pip freeze | grep "astroid" > /dev/null && echo "   [OK] astroid found" || (echo "   [FAIL] astroid MISSING" && exit 1)
	@echo "4. RULE ZERO:"
	@echo "   HEURISTICS DELETED. DYNAMIC DISCOVERY ACTIVE."
	@echo "   [Strict] Site-Packages = Infrastructure"
	@echo "   [Strict] Annotation Priority = Absolute Truth"
	@echo "=================================="

.PHONY: verify-file
verify-file:
	@echo "Auditing $(FILE)..."
	ruff check $(FILE) --select C901
	mypy $(FILE) --strict
	PYTHONPATH=src pylint $(FILE) --fail-under=10.0
	PYTHONPATH=src pytest --cov=src --cov-report=term-missing -m "not slow" | grep $(FILE)

pre-flight:
	excelsior check src
	PYTHONPATH=src pytest

clean:
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .excelsior/*
test:
	PYTHONPATH=src pytest

# Fast tests only, no coverage enforcement. Use during coding for quick regression checks.
test-fast:
	PYTHONPATH=src pytest -m "not slow" --cov=src --cov-report=term-missing --cov-fail-under=0

# Run only slow tests (fix CLI, subprocess-heavy). Use when validating fix feature.
test-slow:
	PYTHONPATH=src pytest -m slow -v --tb=short

# Run all tests including slow (e.g. before release). -m overrides default 'not slow'.
test-all:
	PYTHONPATH=src pytest -m "slow or not slow"

lint:
	PYTHONPATH=src pylint src/ --fail-under=10.0

# Coverage Impact Analysis - Prioritize tests for filesystem-modifying code
coverage-impact:
	@echo "=== Coverage Impact Analysis: Filesystem-Modifying Code ==="
	@mkdir -p .excelsior
	PYTHONPATH=src pytest --cov=src \
		--cov=src/clean_architecture_linter/use_cases/apply_fixes \
		--cov=src/clean_architecture_linter/infrastructure/services/scaffolder \
		--cov=src/clean_architecture_linter/infrastructure/gateways/filesystem_gateway \
		--cov=src/clean_architecture_linter/infrastructure/gateways/libcst_fixer_gateway \
		--cov=src/clean_architecture_linter/infrastructure/services/audit_trail \
		--cov=src/clean_architecture_linter/infrastructure/gateways/transformers \
		--coverage-impact \
		--coverage-impact-top=50 \
		--coverage-impact-json=.excelsior/coverage_impact.json \
		-m "not slow" -q || true
	@echo ""
	@echo "📊 Analyzing filesystem-modifying code..."
	@python3 scripts/analyze_filesystem_coverage.py

# Coverage Impact Analysis - All code
coverage-impact-all:
	@echo "=== Coverage Impact Analysis: All Code ==="
	PYTHONPATH=src pytest --cov=src \
		--coverage-impact \
		--coverage-impact-top=30 \
		--coverage-impact-json=.excelsior/coverage_impact_all.json \
		-m "not slow" || true
	@echo ""
	@echo "📊 Full analysis saved to .excelsior/coverage_impact_all.json"
