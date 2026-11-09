@echo off
setlocal
pushd "%~dp0api"
if not exist ".venv\Scripts\python.exe" (
  echo Backend environment is missing. See api\SETUP.md.
  pause
  exit /b 1
)
.venv\Scripts\python.exe check_database.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m app.seed
if errorlevel 1 goto failed
echo Open http://127.0.0.1:8000/ and use credentials from api\.demo-access.json.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd
exit /b
:failed
echo Setup did not complete. Review the message above.
pause
popd
exit /b 1
