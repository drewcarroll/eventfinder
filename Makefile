.PHONY: install dev run test lint format migrate db-up

install:
	pip install -r requirements-dev.txt

run:
	uvicorn main:app --reload --port 8000

db-up:
	docker compose up -d db

migrate:
	alembic revision --autogenerate -m "auto"
	alembic upgrade head

test:
	pytest

lint:
	ruff check src tests main.py
	mypy src

format:
	black src tests main.py
	ruff check --fix src tests main.py

flutter-run:
	cd client && flutter run
