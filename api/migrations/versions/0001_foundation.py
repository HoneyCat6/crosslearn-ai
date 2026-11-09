"""Create the initial school, identity and assessment foundation.

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('schools', sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(100), nullable=False))
    op.create_table('users', sa.Column('id', sa.String(36), primary_key=True), sa.Column('school_id', sa.String(36), sa.ForeignKey('schools.id'), nullable=False), sa.Column('username', sa.String(100), nullable=False, unique=True), sa.Column('password_hash', sa.String(255), nullable=False), sa.Column('role', sa.String(20), nullable=False))
    op.create_index('ix_users_school_id', 'users', ['school_id'])
    op.create_table('login_sessions', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('csrf_hash', sa.String(64), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('classes', sa.Column('id', sa.String(36), primary_key=True), sa.Column('school_id', sa.String(36), sa.ForeignKey('schools.id'), nullable=False), sa.Column('teacher_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('name', sa.String(80), nullable=False))
    op.create_index('ix_classes_school_id', 'classes', ['school_id'])
    op.create_table('learners', sa.Column('id', sa.String(36), primary_key=True), sa.Column('class_id', sa.String(36), sa.ForeignKey('classes.id'), nullable=False), sa.Column('pseudonym', sa.String(60), nullable=False), sa.Column('consent_status', sa.String(30), nullable=False))
    op.create_index('ix_learners_class_id', 'learners', ['class_id'])
    op.create_table('assessments', sa.Column('id', sa.String(36), primary_key=True), sa.Column('learner_id', sa.String(36), sa.ForeignKey('learners.id', ondelete='CASCADE'), nullable=False), sa.Column('version', sa.String(60), nullable=False), sa.Column('stage', sa.String(20), nullable=False), sa.Column('rotation', sa.Integer(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_assessments_learner_id', 'assessments', ['learner_id'])
    op.create_table('responses', sa.Column('id', sa.String(36), primary_key=True), sa.Column('session_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False), sa.Column('item_id', sa.String(100), nullable=False), sa.Column('chosen_option', sa.Integer(), nullable=False), sa.Column('correct', sa.Boolean(), nullable=False), sa.Column('idempotency_key', sa.String(100), nullable=False), sa.UniqueConstraint('session_id', 'item_id'), sa.UniqueConstraint('session_id', 'idempotency_key'))
    op.create_table('recommendations', sa.Column('id', sa.String(36), primary_key=True), sa.Column('learner_id', sa.String(36), sa.ForeignKey('learners.id', ondelete='CASCADE'), nullable=False), sa.Column('output', sa.JSON(), nullable=False), sa.Column('review_status', sa.String(20), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('audit_events', sa.Column('id', sa.String(36), primary_key=True), sa.Column('school_id', sa.String(36), sa.ForeignKey('schools.id'), nullable=False), sa.Column('actor_id', sa.String(36), nullable=False), sa.Column('action', sa.String(60), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_audit_events_school_id', 'audit_events', ['school_id'])


def downgrade():
    for name in ['audit_events', 'recommendations', 'responses', 'assessments', 'learners', 'classes', 'login_sessions', 'users', 'schools']:
        op.drop_table(name)
