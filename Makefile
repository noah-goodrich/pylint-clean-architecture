.PHONY: handshake
handshake:
	@echo "=== STELLAR PROTOCOL HANDSHAKE ==="
	@ls .agent/*.md | grep -v "_" || (echo "ERROR: .agent/ files must use dashes!" && exit 1)
	@python3 -c "import astroid; print(f'   [OK] Astroid: {astroid.__version__}')"
	@mypy --version > /dev/null || (echo "   [FAIL] Mypy missing!" && exit 1)
	@echo "Complexity: 11 | Typing: Strict (No Any) | Helpers: BANNED"
	@echo "Boundary: stellar-ui-kit is IMMUTABLE"
	@echo "Workflow: Blueprint Approval -> Tests -> Implementation -> verify-file"
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
