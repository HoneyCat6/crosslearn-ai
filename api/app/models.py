from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import ForeignKey, String, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = 'schools'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='teacher')


class Login(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Classroom(Base):
    __tablename__ = 'classes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(80))


class Learner(Base):
    __tablename__ = 'learners'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    class_id: Mapped[str] = mapped_column(ForeignKey('classes.id'), index=True)
    pseudonym: Mapped[str] = mapped_column(String(60))
    consent_status: Mapped[str] = mapped_column(String(30), default='synthetic_demo')


class Assessment(Base):
    __tablename__ = 'assessments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id', ondelete='CASCADE'), index=True)
    version: Mapped[str] = mapped_column(String(60))
    stage: Mapped[str] = mapped_column(String(20), default='baseline')
    rotation: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    assignment_id: Mapped[str | None] = mapped_column(ForeignKey('assignments.id'))
    access_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exposures: Mapped[list] = mapped_column(JSON, default=list)
    lesson_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    hints: Mapped[int] = mapped_column(default=0)


class Response(Base):
    __tablename__ = 'responses'
    __table_args__ = (UniqueConstraint('session_id', 'item_id'), UniqueConstraint('session_id', 'idempotency_key'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('assessments.id', ondelete='CASCADE'))
    item_id: Mapped[str] = mapped_column(String(100))
    chosen_option: Mapped[int]
    correct: Mapped[bool]
    idempotency_key: Mapped[str] = mapped_column(String(100))
    read_aloud: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Recommendation(Base):
    __tablename__ = 'recommendations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id', ondelete='CASCADE'))
    output: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(20), default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey('agent_runs.id', ondelete='CASCADE'))


class ContentBank(Base):
    __tablename__ = 'content_banks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True)
    title: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default='pending_review')
    payload: Mapped[dict] = mapped_column(JSON)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Assignment(Base):
    __tablename__ = 'assignments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    class_id: Mapped[str] = mapped_column(ForeignKey('classes.id'), index=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey('content_banks.id'))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentRun(Base):
    __tablename__ = 'agent_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id', ondelete='CASCADE'), index=True)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'))
    model: Mapped[str] = mapped_column(String(150))
    input_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    error_code: Mapped[str | None] = mapped_column(String(60))
    trace: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Review(Base):
    __tablename__ = 'recommendation_reviews'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey('recommendations.id', ondelete='CASCADE'))
    reviewed_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(20))
    teacher_action: Mapped[str] = mapped_column(String(2000))
    feedback: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
