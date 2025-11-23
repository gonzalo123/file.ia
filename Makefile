.PHONY: test

test:
	./venv/bin/pytest tests/ --cov=src && rm -rf .chainlit .files
