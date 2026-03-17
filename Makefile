.PHONY: help install dev up down logs reset shell db test lint format clean build

help:
	@echo "Oral Narrative Preservation System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Quick Start:"
	@echo "  make up         Start all containers (API + DB + Frontend)"
	@echo "  make down       Stop all containers"
	@echo ""
	@echo "Development:"
	@echo "  install         Install Python dependencies"
	@echo "  dev             Run API locally (requires DB running)"
	@echo "  dev-db          Start only database for local dev"
	@echo ""
	@echo "Docker:"
	@echo "  up              Start all containers"
	@echo "  down            Stop all containers"
	@echo "  build           Rebuild containers"
	@echo "  logs            Show API logs"
	@echo "  logs-all        Show all container logs"
	@echo ""
	@echo "Database:"
	@echo "  reset           Reset database (deletes all data)"
	@echo "  db              Connect to PostgreSQL CLI"
	@echo "  shell           Open API container shell"
	@echo ""
	@echo "Quality:"
	@echo "  test            Run tests"
	@echo "  lint            Run linter"
	@echo "  format          Format code"
	@echo "  clean           Remove generated files"

install:
	cd backend && pip install -r requirements.txt

dev:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-db:
	docker compose up -d db redis
	@echo "Database started. Run 'make dev' to start API."

up:
	docker compose up -d
	@echo ""
	@echo "✅ All containers started!"
	@echo "   Frontend: http://localhost"
	@echo "   API docs: http://localhost/api/docs"

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f api

logs-all:
	docker compose logs -f

reset:
	./scripts/reset-db.sh

shell:
	docker exec -it oral-narratives-api /bin/bash

db:
	docker exec -it oral-narratives-db psql -U narrator -d oral_narratives

test:
	cd backend && pytest tests/ -v

lint:
	ruff check backend/

format:
	ruff format backend/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
