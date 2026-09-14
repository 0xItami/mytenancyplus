.PHONY: install run web test lint typecheck check up down migrate

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

web:
	cd web && npm run dev

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .
	cd web && npm run format:check

typecheck:
	mypy app tests
	cd web && npm run typecheck

check: lint typecheck test
	cd web && npm run build

up:
	docker compose up --build

down:
	docker compose down

migrate:
	alembic upgrade head
