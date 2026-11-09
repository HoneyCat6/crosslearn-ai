"""Check configuration without logging a connection URL or password."""
from sqlalchemy import text
from app.config import settings
from app.db import make_engine


def main():
    engine = None
    try:
        engine = make_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        print('PostgreSQL connection successful.')
        return 0
    except Exception as exc:
        code = getattr(getattr(exc, 'orig', None), 'sqlstate', None)
        messages = {
            '3D000': 'The configured database does not exist. Ask a PostgreSQL administrator to create it.',
            '28P01': 'PostgreSQL rejected the credentials. Check api/.env locally.',
            '42501': 'The database login lacks the required permission.',
        }
        print(messages.get(code, 'Database connection failed. Check local configuration, database existence and service status.'))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
