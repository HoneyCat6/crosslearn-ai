"""Populate a separate, clearly labelled synthetic showcase without changing existing classes."""
import asyncio
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_engine
from .models import *
from .content import seed_content, modes
from .agent import orchestrate
from .service import evidence


def populate(db):
    for user in db.scalars(select(User).where(User.role == 'teacher')):
        name = 'M4 showcase - synthetic fixtures'
        c = db.scalar(select(Classroom).where(Classroom.teacher_id == user.id, Classroom.name == name))
        if c:
            continue
        c = Classroom(school_id=user.school_id, teacher_id=user.id, name=name)
        db.add(c); db.flush()
        data=seed_content()
        bank=ContentBank(school_id=user.school_id,title='Showcase plants - synthetic reviewed fixture',version=data['version'],payload=data,status='approved_demo',reviewed_by=user.id,reviewed_at=now())
        db.add(bank); db.flush()
        assignment=Assignment(class_id=c.id,bank_id=bank.id,created_by=user.id)
        db.add(assignment); db.flush()
        for n in range(3):
            l=Learner(class_id=c.id,pseudonym=f'SHOWCASE-{n+1:03}',consent_status='synthetic_demo')
            db.add(l);db.flush()
            for rotation in range(6):
                started=now()-timedelta(days=21-rotation*2)
                s=Assessment(learner_id=l.id,assignment_id=assignment.id,version=bank.version,stage='results',rotation=rotation,created_at=started,completed_at=started+timedelta(minutes=8),attempts=1,hints=n,
                    exposures=[{'concept':concept['id'],'modality':modes(data,rotation)[concept['id']],'seconds':25+n*5,'transcript':False,'audio_played':modes(data,rotation)[concept['id']]=='audio','version':bank.version,'order':i+1} for i,concept in enumerate(data['concepts'])])
                db.add(s);db.flush()
                for i,q in enumerate(data['baseline']+data['post']):
                    correct=(i+n+rotation)%3!=0 if i<6 else (i+n+rotation)%5!=0
                    option=q['answer'] if correct else (q['answer']+1)%len(q['options'])
                    db.add(Response(session_id=s.id,item_id=q['id'],chosen_option=option,correct=correct,idempotency_key=f'fixture-{q["id"]}'))
            db.flush()
            sessions=evidence(db,l)
            result=asyncio.run(orchestrate({'sessions':sessions,'approved_explanations':[{'concept':x['id'],'text':x['text'],'version':bank.version} for x in data['concepts']]},None))
            run=AgentRun(learner_id=l.id,school_id=user.school_id,model='rules-v1',input_hash=result['input_hash'],status=result['source'],trace=result['trace'],error_code=result['error'])
            db.add(run);db.flush()
            rec=Recommendation(learner_id=l.id,agent_run_id=run.id,output=result['output'],review_status='approved' if n==0 else 'draft')
            db.add(rec);db.flush()
            if n==0: db.add(Review(recommendation_id=rec.id,reviewed_by=user.id,decision='approved',teacher_action=result['output']['teacher_action'],feedback='Synthetic demonstration of teacher review.'))
        db.add(Audit(school_id=user.school_id,actor_id=user.id,action='synthetic_showcase_populated'))
    db.commit()


if __name__ == '__main__':
    with Session(get_engine()) as db: populate(db)
    print('M4 showcase ready: separate classes, balanced histories and review examples. Existing classes preserved.')
