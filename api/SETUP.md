# FastAPI / PostgreSQL setup

The chosen M2 stack is FastAPI and PostgreSQL. Python 3.12.2 was found at `P:\Python\python.exe`; no global PATH change is required.

Run from `P:\innovation\FOI2026\Agentic\crosslearn-ai`:

```powershell
& P:\Python\python.exe -m venv api/.venv
& ./api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt
```

For reproducible installation, use `api/requirements.lock.txt`, which records the versions used by the passing M2 tests. `requirements.txt` is the direct-dependency list.

Install PostgreSQL using the official Windows instructions at https://www.postgresql.org/download/windows/ if it is not already installed. Keep the local server listening on loopback. Create a dedicated non-superuser login and a database owned by that login, named `crosslearn`. Store its connection string in `api/.env`, based on `.env.example`; do not paste passwords into chat.

Verification commands after setup:

```powershell
& ./api/.venv/Scripts/python.exe -m pip check
& ./api/.venv/Scripts/python.exe -c "import fastapi, uvicorn, sqlalchemy, psycopg; print('Backend dependencies available')"
```

Setup is now complete on this machine: Python dependencies are installed in `api/.venv`, PostgreSQL 18.6 is running, and the user created the configured CrossLearn database. The migrations and seed have been applied. See `../docs/M2.md` for the current startup commands, role credentials, walkthrough and verification limits. Previous network restrictions are not evidence of a current setup blocker.
