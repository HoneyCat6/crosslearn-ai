from app.db import make_engine
from app.models import Base
from app.security import passwords, verify_password, new_token, digest
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
import pytest


def test_passwords_are_hashed_and_wrong_passwords_rejected():
    encoded = passwords.hash('synthetic-test-password')
    assert encoded != 'synthetic-test-password'
    assert verify_password('synthetic-test-password', encoded)
    assert not verify_password('incorrect', encoded)


def test_tokens_are_unique_and_only_digest_is_stored():
    token, hashed = new_token()
    assert hashed == digest(token)
    assert token != new_token()[0]
    assert token != hashed


def test_postgres_schema_compiles_with_response_uniqueness():
    sql = '\n'.join(str(CreateTable(t).compile(dialect=postgresql.dialect())) for t in Base.metadata.sorted_tables)
    assert 'UNIQUE (session_id, item_id)' in sql
    assert 'UNIQUE (session_id, idempotency_key)' in sql
    assert 'ON DELETE CASCADE' in sql


def test_database_does_not_silently_fallback_to_sqlite():
    with pytest.raises(RuntimeError):
        make_engine('sqlite://')
