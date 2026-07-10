.PHONY: install test backend frontend seed docker
install:
	python -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt
	cd frontend && npm install
seed:
	PYTHONPATH=backend python -c "from app.core.database import Base,engine,SessionLocal; from app.services.demo_seed import seed_demo; Base.metadata.create_all(engine); db=SessionLocal(); print(seed_demo(db, reset=True)); db.close()"
test:
	cd backend && PYTHONPATH=. pytest -v
	cd frontend && npm run build
backend:
	PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
frontend:
	cd frontend && npm run dev
docker:
	docker compose up --build
