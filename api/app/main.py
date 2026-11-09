from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path
from time import monotonic
from typing import Literal
import csv
import io
import secrets
from urllib.parse import urlsplit

from fastapi import FastAPI, Depends, HTTPException, Request, Response as HTTPResponse
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, delete, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .db import database
from .models import (School, User, Login, Classroom, Learner, Assessment, Response,
                     ContentBank, Assignment, Recommendation, Review, AgentRun, Audit, now)
from .security import digest, new_token, verify_password, passwords
from .auth import current_user, require_role
from .service import classroom, learner, bank_for_session, session_summary, evidence, audit
from .content import modes, validate_content
from .agent import orchestrate, configured_adapter

app = FastAPI(title='CrossLearn AI Demo', version='0.4.0')
app.state.model_adapter = None
hits = defaultdict(deque)
dummy_hash = passwords.hash(secrets.token_urlsafe(32))


@app.middleware('http')
async def boundary(request, call_next):
    host = request.url.hostname
    if host not in ('127.0.0.1', 'localhost', 'testserver'):
        return JSONResponse({'detail': 'This prototype accepts local hosts only.'}, status_code=400)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Cross-origin writes are not permitted.'}, status_code=403)
        length = request.headers.get('content-length', '0')
        if not length.isdigit() or int(length) > 65536 or request.headers.get('transfer-encoding'):
            return JSONResponse({'detail': 'Request body is too large or unsupported.'}, status_code=413)
    # Single-process local prototype limiter; use shared storage before multi-worker hosting.
    stamp = monotonic()
    for key in list(hits):
        while hits[key] and hits[key][0] < stamp - 60:
            hits[key].popleft()
        if not hits[key]:
            del hits[key]
    key = (request.client.host if request.client else 'local', 'login' if request.url.path == '/api/auth/login' else 'api')
    limit = 12 if key[1] == 'login' else 300
    if len(hits[key]) >= limit:
        return JSONResponse({'detail': 'Too many requests. Try again in a minute.'}, status_code=429, headers={'Retry-After': '60'})
    hits[key].append(stamp)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse({'detail': 'Database operation failed. Check the database and migrations; no changes were confirmed.'}, status_code=503)


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Credentials(Input):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


@app.get('/api/health')
def health(db: Session = Depends(database)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'milestone': 'M4-demo', 'research_ready': False, 'synthetic_only': True, 'model_configured': configured_adapter() is not None}


@app.post('/api/auth/login')
def login(body: Credentials, response: HTTPResponse, db: Session = Depends(database)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not verify_password(body.password, user.password_hash if user else dummy_hash) or not user:
        raise HTTPException(401, 'Incorrect username or password.')
    token, token_hash = new_token()
    csrf, csrf_hash = new_token()
    db.execute(delete(Login).where(Login.expires_at < now()))
    db.add(Login(token_hash=token_hash, user_id=user.id, csrf_hash=csrf_hash, expires_at=now() + timedelta(hours=8)))
    audit(db, user, 'signed_in')
    db.commit()
    response.set_cookie('crosslearn_session', token, httponly=True, secure=settings.cookie_secure, samesite='strict', max_age=28800)
    response.set_cookie('crosslearn_csrf', csrf, httponly=False, secure=settings.cookie_secure, samesite='strict', max_age=28800)
    return {'id': user.id, 'username': user.username, 'role': user.role, 'school_id': user.school_id}


@app.get('/api/auth/me')
def me(user: User = Depends(current_user), db: Session = Depends(database)):
    return {'id': user.id, 'username': user.username, 'role': user.role, 'school': db.get(School, user.school_id).name}


@app.post('/api/auth/logout')
def logout(request: Request, response: HTTPResponse, user: User = Depends(current_user), db: Session = Depends(database)):
    db.delete(request.state.login)
    audit(db, user, 'signed_out')
    db.commit()
    response.delete_cookie('crosslearn_session')
    response.delete_cookie('crosslearn_csrf')
    return {'ok': True}


@app.get('/api/teacher/classes')
def classes(user: User = Depends(current_user), db: Session = Depends(database)):
    q = select(Classroom).where(Classroom.school_id == user.school_id)
    if user.role == 'teacher':
        q = q.where(Classroom.teacher_id == user.id)
    return [{'id': c.id, 'name': c.name} for c in db.scalars(q)]


@app.get('/api/teacher/classes/{class_id}')
def class_detail(class_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    c = classroom(db, user, class_id)
    learners = list(db.scalars(select(Learner).where(Learner.class_id == c.id).order_by(Learner.pseudonym)))
    return {'id': c.id, 'name': c.name,
            'learners': [{'id': l.id, 'pseudonym': l.pseudonym, 'consent_status': l.consent_status,
                          'completed_sessions': db.scalar(select(func.count()).select_from(Assessment).where(Assessment.learner_id == l.id, Assessment.stage == 'results'))} for l in learners],
            'assignments': [{'id': a.id, 'title': db.get(ContentBank, a.bank_id).title, 'version': db.get(ContentBank, a.bank_id).version} for a in db.scalars(select(Assignment).where(Assignment.class_id == c.id))]}


@app.get('/api/teacher/content')
def content(user: User = Depends(current_user), db: Session = Depends(database)):
    return [{'id': b.id, 'title': b.title, 'version': b.version, 'status': b.status, 'payload': b.payload,
             'reviewed_at': b.reviewed_at} for b in db.scalars(select(ContentBank).where(ContentBank.school_id == user.school_id))]


class Approval(Input):
    confirm_synthetic_review: Literal[True]


@app.post('/api/teacher/content/{bank_id}/approve')
def approve_content(bank_id: str, body: Approval, user: User = Depends(current_user), db: Session = Depends(database)):
    require_role(user, 'teacher', 'admin')
    bank = db.scalar(select(ContentBank).where(ContentBank.id == bank_id, ContentBank.school_id == user.school_id).with_for_update())
    if not bank:
        raise HTTPException(404, 'Content not found.')
    validate_content(bank.payload)
    bank.status, bank.reviewed_by, bank.reviewed_at = 'approved_demo', user.id, now()
    audit(db, user, 'content_approved_for_synthetic_demo')
    db.commit()
    return {'status': bank.status}


class AssignInput(Input):
    class_id: str = Field(max_length=36)
    bank_id: str = Field(max_length=36)


@app.post('/api/teacher/assignments')
def assign(body: AssignInput, user: User = Depends(current_user), db: Session = Depends(database)):
    c = classroom(db, user, body.class_id, write=True)
    bank = db.scalar(select(ContentBank).where(ContentBank.id == body.bank_id, ContentBank.school_id == user.school_id))
    if not bank:
        raise HTTPException(404, 'Content not found.')
    if bank.status != 'approved_demo':
        raise HTTPException(409, 'Review and approve the sample content first.')
    obj = Assignment(class_id=c.id, bank_id=bank.id, created_by=user.id)
    db.add(obj)
    audit(db, user, 'assignment_created')
    db.commit()
    return {'id': obj.id}


@app.get('/api/teacher/learners/{learner_id}')
def profile(learner_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    obj = learner(db, user, learner_id)
    recs = list(db.scalars(select(Recommendation).where(Recommendation.learner_id == obj.id).order_by(Recommendation.created_at.desc())))
    return {'id': obj.id, 'pseudonym': obj.pseudonym, 'consent_status': obj.consent_status, 'sessions': evidence(db, obj),
            'recommendations': [{'id': r.id, 'output': r.output, 'status': r.review_status, 'created_at': r.created_at,
                                 'run': {'source': db.get(AgentRun, r.agent_run_id).status, 'model': db.get(AgentRun, r.agent_run_id).model,
                                         'error': db.get(AgentRun, r.agent_run_id).error_code, 'trace': db.get(AgentRun, r.agent_run_id).trace},
                                 'reviews': [{'decision': v.decision, 'teacher_action': v.teacher_action, 'feedback': v.feedback, 'created_at': v.created_at} for v in db.scalars(select(Review).where(Review.recommendation_id == r.id).order_by(Review.created_at))]} for r in recs]}


class ConsentInput(Input):
    status: Literal['synthetic_demo', 'withdrawn']


@app.post('/api/teacher/learners/{learner_id}/consent')
def consent(learner_id: str, body: ConsentInput, user: User = Depends(current_user), db: Session = Depends(database)):
    obj = learner(db, user, learner_id, write=True)
    obj.consent_status = body.status
    audit(db, user, 'synthetic_permission_' + body.status)
    db.commit()
    return {'status': obj.consent_status}


@app.delete('/api/teacher/learners/{learner_id}')
def delete_learner(learner_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    obj = learner(db, user, learner_id, write=True)
    db.delete(obj)
    audit(db, user, 'learner_and_linked_records_deleted')
    db.commit()
    return {'deleted': True}


class StartInput(Input):
    assignment_id: str = Field(max_length=36)
    learner_id: str = Field(max_length=36)


@app.post('/api/sessions')
def start_session(body: StartInput, user: User = Depends(current_user), db: Session = Depends(database)):
    obj = learner(db, user, body.learner_id, write=True)
    # Serialize rotation allocation for this learner.
    db.refresh(obj, with_for_update=True)
    if obj.consent_status != 'synthetic_demo':
        raise HTTPException(409, 'Learner participation is withdrawn.')
    a = db.get(Assignment, body.assignment_id)
    if not a or a.class_id != obj.class_id:
        raise HTTPException(404, 'Assignment not found in this class.')
    bank = db.get(ContentBank, a.bank_id)
    if bank.status != 'approved_demo':
        raise HTTPException(409, 'Content approval is required.')
    rotation = db.scalar(select(func.count()).select_from(Assessment).where(Assessment.learner_id == obj.id)) % 6
    token, hashed = new_token()
    session = Assessment(learner_id=obj.id, assignment_id=a.id, version=bank.version, stage='crossword', rotation=rotation,
                         access_hash=hashed, expires_at=now() + timedelta(hours=8))
    db.add(session)
    audit(db, user, 'pupil_session_created')
    db.commit()
    return {'id': session.id, 'token': token, 'rotation': rotation}


def pupil_session(session_id, request, db):
    bearer = request.headers.get('Authorization', '')
    if not bearer.startswith('Bearer '):
        raise HTTPException(401, 'Open the pupil session link supplied by your teacher.')
    s = db.scalar(select(Assessment).where(Assessment.id == session_id).with_for_update())
    if not s or not s.access_hash or not secrets.compare_digest(s.access_hash, digest(bearer[7:])) or s.expires_at <= now():
        raise HTTPException(401, 'Pupil session link is invalid or expired.')
    l = db.get(Learner, s.learner_id)
    if not l or l.consent_status != 'synthetic_demo':
        raise HTTPException(403, 'This session is no longer available.')
    return s


def next_state(db, s):
    data = bank_for_session(db, s).payload
    result = {'id': s.id, 'stage': s.stage, 'version': s.version, 'rotation': s.rotation}
    if s.stage == 'crossword':
        result['puzzle'] = [{k: c[k] for k in ['id', 'number', 'row', 'col', 'direction', 'clue']} | {'length': len(c['word'])} for c in data['concepts']]
    elif s.stage in ('baseline', 'post'):
        answered = set(db.scalars(select(Response.item_id).where(Response.session_id == s.id)))
        pending = [q for q in data[s.stage] if q['id'] not in answered]
        if pending:
            result.update(question={k: v for k, v in pending[0].items() if k != 'answer'}, number=7-len(pending), total=6)
    elif s.stage == 'learn':
        index = len(s.exposures)
        c = data['concepts'][(index + s.rotation // 3) % 3]
        result['lesson'] = {'id': c['id'], 'word': c['word'], 'text': c['text'], 'alt': c['alt'], 'modality': modes(data, s.rotation)[c['id']], 'number': index + 1, 'total': 3}
    elif s.stage == 'results':
        result['summary'] = session_summary(db, s)
        result['answers'] = [{'stem': q['stem'], 'correct_answer': q['options'][q['answer']]} for q in data['baseline'] + data['post']]
    return result


@app.get('/api/pupil/{session_id}/next')
def next_step(session_id: str, request: Request, db: Session = Depends(database)):
    return next_state(db, pupil_session(session_id, request, db))


class CrosswordInput(Input):
    letters: dict[str, str] = Field(max_length=20)


def crossword_cells(data):
    return {f"{c['row'] + (i if c['direction'] == 'down' else 0)}-{c['col'] + (i if c['direction'] == 'across' else 0)}": letter for c in data['concepts'] for i, letter in enumerate(c['word'])}


@app.post('/api/pupil/{session_id}/crossword')
def crossword(session_id: str, body: CrosswordInput, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    if s.stage != 'crossword':
        return next_state(db, s)
    s.attempts += 1
    expected = crossword_cells(bank_for_session(db, s).payload)
    if all(body.letters.get(k, '').upper() == v for k, v in expected.items()):
        s.stage = 'baseline'
    db.commit()
    result = next_state(db, s)
    result['message'] = 'A few letters need another look.' if s.stage == 'crossword' else 'Words discovered!'
    return result


class HintInput(Input):
    cell: str = Field(pattern=r'^\d-\d$')


@app.post('/api/pupil/{session_id}/hint')
def hint(session_id: str, body: HintInput, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    grid = crossword_cells(bank_for_session(db, s).payload)
    if s.stage != 'crossword' or body.cell not in grid:
        raise HTTPException(409, 'Hint unavailable.')
    s.hints += 1
    db.commit()
    return {'cell': body.cell, 'letter': grid[body.cell]}


class AnswerInput(BaseModel):
    # Discard any browser-supplied score/correctness fields; score only the keyed item.
    model_config = ConfigDict(extra='ignore', strict=True)
    item_id: str = Field(max_length=100)
    chosen_option: int = Field(ge=0, le=9)
    idempotency_key: str = Field(min_length=8, max_length=100)
    read_aloud: bool = False


@app.post('/api/pupil/{session_id}/responses')
def answer(session_id: str, body: AnswerInput, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    old = db.scalar(select(Response).where(Response.session_id == s.id, (Response.idempotency_key == body.idempotency_key) | (Response.item_id == body.item_id)))
    if old:
        if (old.item_id, old.chosen_option, old.idempotency_key, old.read_aloud) != (body.item_id, body.chosen_option, body.idempotency_key, body.read_aloud):
            raise HTTPException(409, 'This answer was already submitted with a different payload.')
        return next_state(db, s)
    if s.stage not in ('baseline', 'post'):
        raise HTTPException(409, 'This session is not accepting questions yet.')
    data = bank_for_session(db, s).payload
    state = next_state(db, s)
    if body.item_id != state['question']['id']:
        raise HTTPException(409, 'Answer the current question first.')
    q = next(q for q in data[s.stage] if q['id'] == body.item_id)
    if body.chosen_option >= len(q['options']):
        raise HTTPException(422, 'Invalid answer option.')
    db.add(Response(session_id=s.id, item_id=q['id'], chosen_option=body.chosen_option, correct=body.chosen_option == q['answer'], idempotency_key=body.idempotency_key, read_aloud=body.read_aloud))
    if state['number'] == 6:
        if s.stage == 'baseline':
            s.stage, s.lesson_started_at = 'learn', now()
        else:
            s.stage, s.completed_at = 'results', now()
    db.commit()
    return next_state(db, s)


class ExposureInput(Input):
    concept_id: str = Field(max_length=30)
    transcript: bool = False
    audio_played: bool = False


@app.post('/api/pupil/{session_id}/exposure')
def exposure(session_id: str, body: ExposureInput, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    old = next((e for e in s.exposures if e['concept'] == body.concept_id), None)
    if old:
        if old['transcript'] != body.transcript or old['audio_played'] != body.audio_played:
            raise HTTPException(409, 'Exposure was already recorded differently.')
        return next_state(db, s)
    if s.stage != 'learn':
        raise HTTPException(409, 'Explanation is not available yet.')
    lesson = next_state(db, s)['lesson']
    if body.concept_id != lesson['id']:
        raise HTTPException(409, 'Complete the current explanation first.')
    s.exposures = s.exposures + [{'concept': body.concept_id, 'modality': lesson['modality'], 'seconds': max(0, round((now() - s.lesson_started_at).total_seconds())),
                                'transcript': body.transcript, 'audio_played': body.audio_played, 'version': s.version, 'order': len(s.exposures) + 1}]
    s.lesson_started_at = now()
    if len(s.exposures) == 3:
        s.stage = 'post'
    db.commit()
    return next_state(db, s)


@app.post('/api/teacher/learners/{learner_id}/analyze')
async def analyze(learner_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    obj = learner(db, user, learner_id, write=True)
    if obj.consent_status != 'synthetic_demo':
        raise HTTPException(409, 'Participation is withdrawn.')
    sessions = [s for s in evidence(db, obj) if s['stage'] == 'results']
    if not sessions:
        raise HTTPException(409, 'Complete an assessment before requesting a recommendation.')
    payload = {'sessions': [{'version': s['version'], 'rotation': s['rotation'], 'metrics': s['metrics'], 'exposures': s['exposures']} for s in sessions[-12:]]}
    banks = db.scalars(select(ContentBank).where(ContentBank.school_id == user.school_id, ContentBank.status == 'approved_demo'))
    payload['approved_explanations'] = [{'concept': c['id'], 'text': c['text'], 'version': b.version} for b in banks for c in b.payload['concepts']]
    result = await orchestrate(payload, app.state.model_adapter or configured_adapter())
    db.refresh(obj)
    if obj.consent_status != 'synthetic_demo':
        raise HTTPException(409, 'Participation was withdrawn during analysis.')
    run = AgentRun(learner_id=obj.id, school_id=user.school_id, model=settings.model_name if result['source'] == 'model' else 'rules-v1', input_hash=result['input_hash'], status=result['source'], error_code=result['error'], trace=result['trace'])
    db.add(run)
    db.flush()
    rec = Recommendation(learner_id=obj.id, agent_run_id=run.id, output=result['output'])
    db.add(rec)
    audit(db, user, 'recommendation_drafted')
    db.commit()
    return {'id': rec.id, 'output': rec.output, 'source': result['source'], 'error': result['error']}


class ReviewInput(Input):
    decision: Literal['approved', 'edited', 'rejected']
    teacher_action: str = Field(min_length=1, max_length=2000)
    feedback: str = Field(max_length=2000, default='')


@app.post('/api/teacher/recommendations/{recommendation_id}/review')
def review(recommendation_id: str, body: ReviewInput, user: User = Depends(current_user), db: Session = Depends(database)):
    rec = db.scalar(select(Recommendation).where(Recommendation.id == recommendation_id).with_for_update())
    if not rec:
        raise HTTPException(404, 'Recommendation not found.')
    learner(db, user, rec.learner_id, write=True)
    db.add(Review(recommendation_id=rec.id, reviewed_by=user.id, decision=body.decision, teacher_action=body.teacher_action, feedback=body.feedback))
    rec.review_status = body.decision
    audit(db, user, 'recommendation_' + body.decision)
    db.commit()
    return {'status': rec.review_status}


@app.get('/api/research/export/{class_id}')
def export(class_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    require_role(user, 'researcher', 'admin')
    classroom(db, user, class_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['learner_id', 'session_id', 'content_version', 'rotation', 'concept', 'modality', 'baseline_correct', 'baseline_total', 'post_correct', 'post_total', 'gain_pp', 'seconds', 'transcript', 'audio_played', 'read_aloud_count', 'retention_answered', 'retention_correct'])
    for obj in db.scalars(select(Learner).where(Learner.class_id == class_id, Learner.consent_status == 'synthetic_demo')):
        for s in evidence(db, obj):
            if s['stage'] != 'results':
                continue
            for r in s['metrics']:
                e = next(e for e in s['exposures'] if e['concept'] == r['concept'])
                writer.writerow([obj.id, s['id'], s['version'], s['rotation'], r['concept'], r['modality'], r['baseline_correct'], r['baseline_total'], r['post_correct'], r['post_total'], r['gain_pp'], e['seconds'], e['transcript'], e['audio_played'], s['read_aloud_count'], s['retention']['answered'], s['retention']['correct']])
    audit(db, user, 'deidentified_class_export')
    db.commit()
    return HTTPResponse(buffer.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="crosslearn-research.csv"'})


@app.get('/api/admin/audit')
def audit_log(user: User = Depends(current_user), db: Session = Depends(database)):
    require_role(user, 'admin')
    return [{'id': e.id, 'action': e.action, 'actor_id': e.actor_id, 'created_at': e.created_at} for e in db.scalars(select(Audit).where(Audit.school_id == user.school_id).order_by(Audit.created_at.desc()).limit(200))]


class ContentDraft(Input):
    title: str = Field(min_length=1, max_length=100)
    payload: dict


@app.post('/api/teacher/content')
def create_content(body: ContentDraft, user: User = Depends(current_user), db: Session = Depends(database)):
    require_role(user, 'teacher', 'admin')
    try:
        validate_content(body.payload)
        if {c['id'] for c in body.payload['concepts']} != {'root','stem','moss'}:
            raise ValueError('Current renderer supports the three plant concepts only.')
        version=body.payload['version']
        if not isinstance(version,str) or not 1 <= len(version) <= 60:
            raise ValueError('Invalid version.')
        for c in body.payload['concepts']:
            if not all(isinstance(c[k],str) and c[k] for k in ('word','clue','text','alt')):
                raise ValueError('Missing concept text.')
        for phase in ('baseline','post'):
            for q in body.payload[phase]:
                if not isinstance(q['stem'],str) or not q['stem'] or not all(isinstance(o,str) and o for o in q['options']):
                    raise ValueError('Invalid question text.')
    except (AssertionError,KeyError,TypeError,ValueError):
        raise HTTPException(422,'Invalid content. Preserve the three-concept grid and provide 6 unique keyed items per phase, scripts, diagram descriptions and a new version.')
    if db.scalar(select(ContentBank).where(ContentBank.school_id==user.school_id,ContentBank.version==version)):
        raise HTTPException(409,'Use a new content version; published snapshots are immutable.')
    bank=ContentBank(school_id=user.school_id,title=body.title,version=version,payload=body.payload,status='pending_review')
    db.add(bank);audit(db,user,'content_version_drafted');db.commit()
    return {'id':bank.id,'status':bank.status}


@app.get('/api/research/report/{class_id}')
def research_report(class_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    classroom(db, user, class_id)
    sessions = [s for l in db.scalars(select(Learner).where(Learner.class_id == class_id, Learner.consent_status == 'synthetic_demo')) for s in evidence(db, l) if s['stage'] == 'results']
    rotations = {str(i + 1): sum(s['rotation'] == i for s in sessions) for i in range(6)}
    rows = [r for s in sessions for r in s['metrics']]
    return {'synthetic_only': True, 'study_mode': 'technical_pilot', 'completed_sessions': len(sessions),
            'rotations': rotations, 'balanced': len(set(rotations.values())) == 1 and bool(sessions),
            'mean_gain_pp': round(sum(r['gain_pp'] for r in rows) / len(rows), 1) if rows else None,
            'calibration': 'uncalibrated', 'effectiveness_claim_permitted': False,
            'limitations': ['Synthetic outcomes are fixtures, not effectiveness evidence.', 'Two items per concept give coarse scores.', 'Content difficulty requires teacher calibration.', 'Repeated items are practice, not independent trials.']}


@app.get('/api/pupil/{session_id}/offline-pack')
def offline_pack(session_id: str, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    data = bank_for_session(db, s).payload
    result = {'state': next_state(db, s), 'expires_at': s.expires_at.isoformat(), 'questions': []}
    if s.stage in ('baseline', 'post'):
        answered = set(db.scalars(select(Response.item_id).where(Response.session_id == s.id)))
        result['questions'] = [{k: v for k, v in q.items() if k != 'answer'} for q in data[s.stage] if q['id'] not in answered]
    return result


RETENTION_ITEMS = [
    {'id':'ret-root-1-v1','concept':'root','stem':'Which structure anchors a bean plant below ground?', 'options':['Roots','Petals','Fruit'],'answer':0},
    {'id':'ret-root-2-v1','concept':'root','stem':'Soil water first enters a young sunflower mainly through its?', 'options':['Flowers','Roots','Seeds'],'answer':1},
    {'id':'ret-moss-1-v1','concept':'moss','stem':'Which place would most likely support a patch of moss?', 'options':['A dry hot oven','A shady wet wall','A sealed empty bottle'],'answer':1},
    {'id':'ret-moss-2-v1','concept':'moss','stem':'How can a small moss plant obtain water?', 'options':['Through its surface','By eating insects','Through flower petals'],'answer':0},
    {'id':'ret-stem-1-v1','concept':'stem','stem':'Which part links a plant?s roots to its leaves?', 'options':['Fruit','Seed coat','Stem'],'answer':2},
    {'id':'ret-stem-2-v1','concept':'stem','stem':'A plant?s leaves are held up by which structure?', 'options':['Stem','Soil grains','Roots only'],'answer':0}]


@app.post('/api/teacher/sessions/{session_id}/retention-access')
def retention_access(session_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    s=db.scalar(select(Assessment).where(Assessment.id==session_id).with_for_update())
    if not s: raise HTTPException(404,'Session not found.')
    obj=learner(db,user,s.learner_id,write=True)
    if obj.consent_status!='synthetic_demo' or s.stage!='results' or not s.completed_at or now()<s.completed_at+timedelta(days=7):
        raise HTTPException(409,'Retention is not available yet.')
    token,hashed=new_token();s.access_hash=hashed;s.expires_at=now()+timedelta(hours=8)
    audit(db,user,'retention_access_issued');db.commit()
    return {'id':s.id,'token':token,'rotation':s.rotation}


@app.get('/api/pupil/{session_id}/retention')
def retention_state(session_id: str, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    if s.stage != 'results':
        raise HTTPException(409, 'Finish the original assessment first.')
    due = s.completed_at + timedelta(days=7)
    responses = list(db.scalars(select(Response).where(Response.session_id == s.id, Response.item_id.like('ret-%'))))
    answered = {r.item_id for r in responses}
    pending = [q for q in RETENTION_ITEMS if q['id'] not in answered]
    return {'due_at': due.isoformat(), 'available': now() >= due, 'complete': not pending,
            'question': {k:v for k,v in pending[0].items() if k != 'answer'} if pending and now() >= due else None,
            'number': len(answered)+1, 'total':6,
            'correct': sum(r.correct for r in responses) if not pending else None}


@app.post('/api/pupil/{session_id}/retention')
def retention_answer(session_id: str, body: AnswerInput, request: Request, db: Session = Depends(database)):
    s = pupil_session(session_id, request, db)
    state = retention_state(session_id, request, db)
    old = db.scalar(select(Response).where(Response.session_id == s.id, (Response.item_id == body.item_id) | (Response.idempotency_key == body.idempotency_key)))
    if old:
        if (old.item_id,old.chosen_option,old.idempotency_key,old.read_aloud)!=(body.item_id,body.chosen_option,body.idempotency_key,body.read_aloud):
            raise HTTPException(409,'Retention answer conflicts with a saved response.')
        return state
    if not state['available'] or not state['question'] or state['question']['id'] != body.item_id:
        raise HTTPException(409,'Retention assessment is not due or this is not the current item.')
    q = next(q for q in RETENTION_ITEMS if q['id'] == body.item_id)
    if body.chosen_option >= len(q['options']):
        raise HTTPException(422,'Invalid option.')
    db.add(Response(session_id=s.id,item_id=q['id'],chosen_option=body.chosen_option,correct=body.chosen_option==q['answer'],idempotency_key=body.idempotency_key,read_aloud=body.read_aloud))
    db.commit()
    return retention_state(session_id, request, db)


public = Path(__file__).resolve().parents[1] / 'public'
public.mkdir(exist_ok=True)
app.mount('/assets', StaticFiles(directory=public), name='assets')


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(public / 'index.html')


@app.get('/sw.js', include_in_schema=False)
def service_worker():
    return FileResponse(public / 'sw.js', media_type='application/javascript', headers={'Service-Worker-Allowed': '/'})
