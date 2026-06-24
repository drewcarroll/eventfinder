.PHONY: install dev run test lint format migrate revision db-up flutter-run emulator

install:
	pip install -r requirements-dev.txt

run:
	uvicorn main:app --reload --port 8000

db-up:
	docker compose up -d db

# Apply all pending migrations (the normal path; run after db-up).
migrate:
	alembic upgrade head

# Author a new migration from model changes: make revision m="describe change".
revision:
	alembic revision --autogenerate -m "$(m)"

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

# One command for the full stack on an emulator: Postgres -> migrations ->
# FastAPI backend -> Flutter app. Override target with e.g.
#   make emulator EMULATOR_ID=apple_ios_simulator API_HOST=localhost
emulator: export EMULATOR_ID := $(EMULATOR_ID)
emulator: export API_HOST := $(API_HOST)
emulator: export API_PORT := $(API_PORT)
emulator:
	./scripts/dev-emulator.sh
