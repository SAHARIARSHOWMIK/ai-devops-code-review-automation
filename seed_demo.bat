@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONPATH=backend
python -c "from app.core.database import Base,engine,SessionLocal; from app.services.demo_seed import seed_demo; Base.metadata.create_all(engine); db=SessionLocal(); print(seed_demo(db, reset=True)); db.close()"
pause
