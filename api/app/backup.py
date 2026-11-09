"""Create a PostgreSQL custom-format local backup without logging connection secrets."""
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.engine import make_url
from .config import settings


def backup():
    executable=shutil.which('pg_dump')
    if not executable:
        candidates=sorted(Path('C:/Program Files/PostgreSQL').glob('*/bin/pg_dump.exe'))
        executable=str(candidates[-1]) if candidates else None
    if not executable: raise SystemExit('pg_dump is unavailable. Install PostgreSQL client tools.')
    url=make_url(settings.database_url)
    folder=Path(__file__).resolve().parents[1]/'backups';folder.mkdir(exist_ok=True)
    target=folder/('crosslearn-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.dump')
    env=os.environ.copy();env['PGPASSWORD']=url.password or ''
    args=[executable,'--host',url.host or 'localhost','--port',str(url.port or 5432),'--username',url.username or '', '--dbname',url.database,'--format=custom','--no-owner','--file',str(target)]
    result=subprocess.run(args,env=env,capture_output=True)
    if result.returncode: raise SystemExit('Backup failed. Check PostgreSQL connectivity and backup permissions.')
    print('Created local backup:',target.name)


if __name__=='__main__': backup()
