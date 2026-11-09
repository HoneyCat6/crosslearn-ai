from datetime import timedelta
from sqlalchemy import select, func
from app.models import Assessment, Classroom, now
from app.main import RETENTION_ITEMS
from app.demo import populate
from test_workflow import complete, setup_session


def test_phase_pack_and_report_permissions(environment):
    teacher,pupil,cid,lid,assignment,s=setup_session(environment)
    pack=pupil.get(f"/api/pupil/{s['id']}/offline-pack").json()
    assert pack['state']['stage']=='crossword' and not pack['questions']
    assert 'answer' not in str(pack) and 'lesson' not in str(pack)
    other=environment['client']('teacher.b')
    assert other.get(f'/api/research/report/{cid}').status_code==404
    assert teacher.get(f'/api/research/report/{cid}').json()['effectiveness_claim_permitted'] is False


def test_retention_due_scoring_and_retries(environment):
    teacher,pupil,cid,lid,a,s=complete(environment)
    url=f"/api/pupil/{s['id']}/retention"
    assert pupil.get(url).json()['available'] is False
    with environment['db']() as db:
        db.get(Assessment,s['id']).completed_at=now()-timedelta(days=8);db.commit()
    for q in RETENTION_ITEMS:
        body={'item_id':q['id'],'chosen_option':q['answer'],'idempotency_key':'retention-'+q['id']}
        r=pupil.post(url,json=body)
        assert r.status_code==200,r.text
        assert pupil.post(url,json=body).status_code==200
        assert pupil.post(url,json=body|{'chosen_option':(q['answer']+1)%3}).status_code==409
    assert r.json()['complete'] and r.json()['correct']==6
    assert teacher.get(f'/api/teacher/learners/{lid}').json()['sessions'][0]['retention']['correct']==6


def test_showcase_idempotency_and_balance(environment):
    with environment['db']() as db:
        populate(db); count=db.scalar(select(func.count()).select_from(Assessment))
        populate(db); assert db.scalar(select(func.count()).select_from(Assessment))==count==36
    teacher=environment['client']('teacher.a')
    c=next(c for c in teacher.get('/api/teacher/classes').json() if 'showcase' in c['name'])
    report=teacher.get(f"/api/research/report/{c['id']}").json()
    assert report['balanced'] and report['completed_sessions']==18


def test_content_version_workflow(environment):
    from app.content import seed_content
    teacher=environment['client']('teacher.a')
    data=seed_content();data['version']='science-demo-v2'
    r=teacher.post('/api/teacher/content',json={'title':'Revised sample','payload':data})
    assert r.status_code==200,r.text
    assert r.json()['status']=='pending_review'
    assert teacher.post('/api/teacher/content',json={'title':'Duplicate','payload':data}).status_code==409
    researcher=environment['client']('researcher.a')
    assert researcher.post('/api/teacher/content',json={'title':'Denied','payload':data}).status_code==403
    data['baseline']=[]
    assert teacher.post('/api/teacher/content',json={'title':'Invalid','payload':data}).status_code==422
