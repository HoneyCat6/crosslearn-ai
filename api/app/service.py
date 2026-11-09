from fastapi import HTTPException
from sqlalchemy import select
from .models import Classroom, Learner, Assignment, ContentBank, Assessment, Response, Audit
from .content import metrics


def classroom(db, user, class_id, write=False):
    obj = db.scalar(select(Classroom).where(Classroom.id == class_id, Classroom.school_id == user.school_id))
    if not obj or (user.role == 'teacher' and obj.teacher_id != user.id):
        raise HTTPException(404, 'Class not found.')
    if write and user.role not in ('teacher', 'admin'):
        raise HTTPException(403, 'Your role cannot change classroom records.')
    return obj


def learner(db, user, learner_id, write=False):
    obj = db.get(Learner, learner_id)
    if not obj:
        raise HTTPException(404, 'Learner not found.')
    classroom(db, user, obj.class_id, write)
    return obj


def bank_for_session(db, session):
    assignment = db.get(Assignment, session.assignment_id)
    if not assignment:
        raise HTTPException(409, 'Assignment is unavailable.')
    bank = db.get(ContentBank, assignment.bank_id)
    if not bank or bank.version != session.version:
        raise HTTPException(409, 'Content version is unavailable.')
    return bank


def session_summary(db, session):
    bank = bank_for_session(db, session)
    responses = list(db.scalars(select(Response).where(Response.session_id == session.id)))
    return {'id': session.id, 'stage': session.stage, 'version': session.version, 'rotation': session.rotation,
            'created_at': session.created_at.isoformat(), 'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'metrics': metrics(bank.payload, responses, session.rotation) if session.stage == 'results' else [],
            'exposures': session.exposures, 'attempts': session.attempts, 'hints': session.hints,
            'retention': {'answered': sum(r.item_id.startswith('ret-') for r in responses), 'correct': sum(r.correct for r in responses if r.item_id.startswith('ret-'))},
            'read_aloud_count': sum(r.read_aloud for r in responses)}


def evidence(db, obj):
    sessions = db.scalars(select(Assessment).where(Assessment.learner_id == obj.id).order_by(Assessment.created_at))
    return [session_summary(db, s) for s in sessions]


def audit(db, user, action):
    # Avoid retaining learner identifiers or payloads in audit records after deletion.
    db.add(Audit(school_id=user.school_id, actor_id=user.id, action=action))
