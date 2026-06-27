.PHONY: up down migrate seed test-backend test-flutter lint-backend format logs

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python scripts/seed.py

test-backend:
	cd backend && pytest tests/ -v --tb=short

test-flutter:
	cd frontend && flutter test

lint-backend:
	cd backend && ruff check app/ && mypy app/

format:
	cd backend && black app/ tests/

logs:
	docker-compose logs -f backend
