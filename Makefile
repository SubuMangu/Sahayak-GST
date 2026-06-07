.PHONY: help backend frontend test build up down install

help:
	@echo "Sahayak GST — common tasks"
	@echo "  make install    Install backend + frontend deps"
	@echo "  make backend    Run FastAPI dev server (SQLite fallback)"
	@echo "  make frontend   Run Vite dev server"
	@echo "  make test       Run backend test suite"
	@echo "  make build      Build the frontend"
	@echo "  make up         docker compose up --build"
	@echo "  make down       docker compose down"

install:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

test:
	cd backend && . .venv/bin/activate && pytest -q

build:
	cd frontend && npm run build

up:
	docker compose up --build

down:
	docker compose down
