.PHONY: install run test lint typecheck check up down migrate

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy app tests

check: lint typecheck test

up:
	docker compose up --build

down:
	docker compose down

migrate:
	alembic upgrade head

