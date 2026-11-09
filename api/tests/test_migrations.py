from pathlib import Path
from uuid import uuid4
from alembic.config import Config
from alembic import command
from sqlalchemy import text, inspect
from sqlalchemy.engine import make_url
from app.config import settings
from app.db import get_engine, make_engine


def test_postgresql_migrations_upgrade_and_downgrade(monkeypatch):
    original = settings.database_url
    schema = 'migration_test_' + uuid4().hex
    base = get_engine()
    with base.begin() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(original).update_query_dict({'options': f'-csearch_path={schema}'}).render_as_string(hide_password=False)
    monkeypatch.setattr(settings, 'database_url', url)
    config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    check = make_engine(url)
    try:
        command.upgrade(config, 'head')
        assert 'recommendation_reviews' in inspect(check).get_table_names()
        assert 'content_banks' in inspect(check).get_table_names()
        command.downgrade(config, 'base')
        assert inspect(check).get_table_names() == ['alembic_version']
    finally:
        check.dispose()
        with base.begin() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
