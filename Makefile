.PHONY: clean test test-all

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

test:
	pytest

test-all:
	pytest tests/

lint:
	ruff check
	pylint src/
