@echo off
setlocal
pushd "%~dp0api"
.venv\Scripts\python.exe check_database.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m app.seed
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m app.demo
if errorlevel 1 goto failed
echo Open http://127.0.0.1:8000/ - credentials: api\.demo-access.json
echo Select the M4 showcase class for populated evidence or the original class to play.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd
exit /b
:failed
echo Demo setup failed. See docs\M4.md.
pause
popd
exit /b 1
