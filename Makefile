.PHONY: handshake
handshake:
	@echo "=== STELLAR PROTOCOL HANDSHAKE (Augmented) ==="
	@echo "1. INTERPRETER AUDIT:"
	@python3 -c "import sys; print(f'   [INFO] StdLib Modules: {len(sys.stdlib_module_names)}');"
	@python3 -c "import sysconfig; print(f'   [INFO] StdLib Path: {sysconfig.get_path(\"stdlib\")}')"
	@echo "2. STUB AUDIT:"
	@pip freeze | grep "types-astroid" > /dev/null && echo "   [OK] types-astroid found" || (echo "   [FAIL] types-astroid MISSING" && exit 1)
	@echo "3. RULE ZERO:"
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
	pytest --cov=src --cov-report=term-missing | grep $(FILE)

pre-flight:
	ruff check . --select C901
	mypy src/ --strict
	PYTHONPATH=src pylint src/ --fail-under=10.0
	pytest tests/functional/test_lod_benchmarks.py

clean:
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

test:
	pytest --cov=src --cov-report=term-missing --cov-report=json --cov-fail-under=80 --coverage-impact

lint:
	PYTHONPATH=src pylint src/ --fail-under=10.0
