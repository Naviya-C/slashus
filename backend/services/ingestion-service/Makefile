.PHONY: install test lint check run vision

install:
	python -m pip install -e ".[dev,vision]"

test:
	pytest

lint:
	ruff check src tests
	mypy src

check:
	python -m compileall -q src tests
	pytest
	ruff check src tests

run:
	ingestion-service serve

vision:
	ingestion-service vision-worker

