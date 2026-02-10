.PHONY: setup-backend run-backend test-backend

setup-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run-backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

test-backend:
	cd backend && . .venv/bin/activate && pytest
