from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from functools import lru_cache
from .config import settings


def make_engine(url: str):
    if not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Configure DATABASE_URL with a postgresql+psycopg connection in api/.env.')
    return create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 5})


@lru_cache
def get_engine():
    return make_engine(settings.database_url)


def database():
    with sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session
