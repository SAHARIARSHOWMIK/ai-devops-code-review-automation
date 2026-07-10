@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python launcher not found. Install Python 3.12 and try again.& pause & exit /b 1)
py -3.12 -m venv .venv || (echo Python 3.12 is required.& pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
if not exist .env copy .env.example .env
pushd backend
alembic upgrade head
popd
pushd frontend
call npm install
popd
echo.
echo Setup complete. Run seed_demo.bat once, then start_backend.bat and start_frontend.bat.
pause
