.PHONY: install test backend frontend seed docker

install:
	python -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci --include=dev --no-audit --no-fund

seed:
	PYTHONPATH=backend python -c "from app.core.database import Base,engine,SessionLocal; from app.services.demo_seed import seed_demo; Base.metadata.create_all(engine); db=SessionLocal(); print(seed_demo(db, reset=True)); db.close()"

test:
	cd backend && PYTHONPATH=. ruff format --check app tests
	cd backend && PYTHONPATH=. ruff check app tests
	cd backend && PYTHONPATH=. bandit -q -ll -r app
	cd backend && PYTHONPATH=. python -m compileall -q app tests
	cd backend && PYTHONPATH=. pytest --cov=app --cov-report=term-missing
	cd frontend && npm ci --include=dev --no-audit --no-fund
	cd frontend && npm run lint
	cd frontend && npm run build
	cd frontend && npm audit --audit-level=high

backend:
	PYTHONPATH=backend uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

docker:
	docker compose up --build
