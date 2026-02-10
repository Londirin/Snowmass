.PHONY: setup-backend dev run-backend test-backend

setup-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

run-backend: dev

test-backend:
	cd backend && . .venv/bin/activate && pytest
