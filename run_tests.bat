@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat || exit /b 1
set PYTHONPATH=backend

pushd backend
ruff format --check app tests || (popd & pause & exit /b 1)
ruff check app tests || (popd & pause & exit /b 1)
bandit -q -ll -r app || (popd & pause & exit /b 1)
python -m compileall -q app tests || (popd & pause & exit /b 1)
pytest --cov=app --cov-report=term-missing || (popd & pause & exit /b 1)
popd

pushd frontend
call npm ci --include=dev --no-audit --no-fund || (popd & pause & exit /b 1)
call npm run lint || (popd & pause & exit /b 1)
call npm run build || (popd & pause & exit /b 1)
call npm audit --audit-level=high || (popd & pause & exit /b 1)
popd

echo.
echo All local checks passed.
pause
