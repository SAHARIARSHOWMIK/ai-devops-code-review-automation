@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONPATH=backend
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
