@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONPATH=backend
celery -A app.workers.celery_app.celery worker --loglevel=INFO
