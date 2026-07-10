@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONPATH=backend
pushd backend
pytest -v
popd
pushd frontend
call npm run build
popd
pause
