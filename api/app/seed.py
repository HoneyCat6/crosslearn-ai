"""Idempotent synthetic fixtures; passwords are generated locally, never served to browsers."""
import json
import secrets
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import School, User, Classroom, Learner, ContentBank
from .content import seed_content, validate_content
from .db import get_engine
from .security import passwords


def seed(db, credentials):
    payload = seed_content()
    validate_content(payload)
    for label in ['A', 'B']:
        name = f'Demo School {label}'
        school = db.scalar(select(School).where(School.name == name))
        if not school:
            school = School(name=name)
            db.add(school)
            db.flush()
        roles = ['teacher', 'admin', 'researcher'] if label == 'A' else ['teacher']
        teacher = None
        for role in roles:
            username = f'{role}.{label.lower()}'
            user = db.scalar(select(User).where(User.username == username))
            if not user:
                user = User(school_id=school.id, username=username, password_hash=passwords.hash(credentials[username]), role=role)
                db.add(user)
                db.flush()
            if role == 'teacher':
                teacher = user
        classroom = db.scalar(select(Classroom).where(Classroom.school_id == school.id))
        if not classroom:
            classroom = Classroom(school_id=school.id, teacher_id=teacher.id, name='Year 4 · Science explorers')
            db.add(classroom)
            db.flush()
            for n in range(1, 4):
                db.add(Learner(class_id=classroom.id, pseudonym=f'DEMO-{label}-{n:03}', consent_status='synthetic_demo'))
        if not db.scalar(select(ContentBank).where(ContentBank.school_id == school.id)):
            db.add(ContentBank(school_id=school.id, title='Plants & their hidden wonders', version=payload['version'], payload=payload))
    db.commit()


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / '.demo-access.json'
    credentials = json.loads(path.read_text()) if path.exists() else {u: secrets.token_urlsafe(18) for u in ['teacher.a', 'admin.a', 'researcher.a', 'teacher.b']}
    with Session(get_engine()) as db:
        seed(db, credentials)
    path.write_text(json.dumps(credentials, indent=2), encoding='utf-8')
    print('Synthetic schools, accounts, classes, learners and pending content are ready.')
    print('Local credentials: api/.demo-access.json (not served or committed).')
