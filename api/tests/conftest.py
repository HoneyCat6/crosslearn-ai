from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db import get_engine, database
from app.config import settings
from app.models import Base
from app.seed import seed
from app.main import app, hits

PASSWORD = 'Synthetic-test-only-37!'


@pytest.fixture
def environment():
    # Each test owns a new PostgreSQL schema; never delete or truncate app tables.
    schema = 'test_' + uuid4().hex
    with get_engine().begin() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(settings.database_url, connect_args={'options': f'-csearch_path={schema}', 'connect_timeout': 5})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        seed(db, {u: PASSWORD for u in ['teacher.a', 'admin.a', 'researcher.a', 'teacher.b']})

    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[database] = override
    hits.clear()
    app.state.model_adapter = None
    clients = []

    def client(username=None):
        c = TestClient(app)
        clients.append(c)
        if username:
            r = c.post('/api/auth/login', json={'username': username, 'password': PASSWORD})
            assert r.status_code == 200, r.text
            c.headers['X-CSRF-Token'] = c.cookies['crosslearn_csrf']
        return c

    yield {'client': client, 'db': factory, 'engine': engine}
    for c in clients:
        c.close()
    app.dependency_overrides.clear()
    app.state.model_adapter = None
    engine.dispose()
    with get_engine().begin() as c:
        c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
