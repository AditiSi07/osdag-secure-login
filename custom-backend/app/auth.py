from datetime import datetime

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Session, User
from app.routes.auth import hash_token


def get_current_user(
    authorization: str = Header(default=None),
    db: DBSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    raw_token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)

    session = db.query(Session).filter(Session.token_hash == token_hash).first()

    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user