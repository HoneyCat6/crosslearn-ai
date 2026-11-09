from datetime import timedelta
import secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .db import database
from .models import Login, User, now
from .security import digest


def current_user(request: Request, db: Session = Depends(database)) -> User:
    token = request.cookies.get('crosslearn_session', '')
    login = db.get(Login, digest(token)) if token else None
    if not login or login.expires_at <= now():
        raise HTTPException(401, 'Sign in to continue.')
    user = db.get(User, login.user_id)
    if not user:
        raise HTTPException(401, 'Sign in to continue.')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        csrf = request.headers.get('X-CSRF-Token', '')
        if not csrf or not secrets.compare_digest(digest(csrf), login.csrf_hash):
            raise HTTPException(403, 'Invalid request token. Refresh and try again.')
    request.state.login = login
    return user


def require_role(user, *roles):
    if user.role not in roles:
        raise HTTPException(403, 'Your role cannot perform this action.')
