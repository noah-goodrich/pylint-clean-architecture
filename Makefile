.PHONY: clean test test-all

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

test:
	@if pytest --help | grep -q "coverage-impact"; then \
		pytest --coverage-impact; \
	else \
		pytest; \
	fi

test-all:
	pytest tests/

lint:
	ruff check
	@if pip show pylint-clean-architecture > /dev/null 2>&1 || [ -d "src/clean_architecture_linter" ]; then \
		pylint --load-plugins=clean_architecture_linter src/; \
	else \
		pylint src/; \
	fi
