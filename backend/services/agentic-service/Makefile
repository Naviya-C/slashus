.PHONY: install proto test lint fmt typecheck check run tools migrate docker
install:; uv pip install -e ".[dev]"
proto:; bash scripts/gen_proto.sh
test:; PYTHONPATH=src pytest -q
lint:; ruff check src tests && ruff format --check src tests
fmt:; ruff format src tests && ruff check --fix src tests
typecheck:; mypy src
check: lint typecheck test
run:; PYTHONPATH=src python -m agentic_service serve
tools:; PYTHONPATH=src python -m agentic_service tools
migrate:; alembic upgrade head
docker:; docker build -t slashus/agentic-service:4.0.0 .
