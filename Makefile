.PHONY: test

test:
	./venv/bin/pytest tests/ --cov=src
