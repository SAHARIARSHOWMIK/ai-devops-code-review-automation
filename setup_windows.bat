@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul || (echo Python launcher not found. Install Python 3.12 and try again.& pause & exit /b 1)
where node >nul 2>nul || (echo Node.js not found. Install Node.js 22.12 or newer and try again.& pause & exit /b 1)
where npm >nul 2>nul || (echo npm not found. Reinstall Node.js 22.12 or newer and try again.& pause & exit /b 1)

py -3.12 -m venv .venv || (echo Python 3.12 is required.& pause & exit /b 1)
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r backend\requirements-dev.txt || exit /b 1

if not exist .env copy .env.example .env >nul

pushd backend
alembic upgrade head || (popd & pause & exit /b 1)
popd

pushd frontend
call npm ci --include=dev --no-audit --no-fund || (popd & pause & exit /b 1)
popd

echo.
echo Setup complete. Run seed_demo.bat once, then start_backend.bat and start_frontend.bat.
pause
