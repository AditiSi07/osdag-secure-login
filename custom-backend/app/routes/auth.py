import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Header

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, Session
from app.schemas import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse, LoginUserInfo

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5
SESSION_HOURS = 24


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: DBSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with that email already exists")

    user = User(
        email=payload.email,
        password_hash=pwd_context.hash(payload.password),
        display_name=payload.email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(id=str(user.id), email=user.email)
@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DBSession = Depends(get_db)):
    GENERIC_ERROR = "Invalid email or password"

    user = db.query(User).filter(User.email == payload.email).first()

    # Locked out? Check this even before verifying the password.
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")

    # Deliberately the SAME error and SAME status code whether the user
    # doesn't exist, or exists but the password is wrong — never let a
    # client distinguish the two cases.
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        if user:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_attempts = 0
            db.commit()
        raise HTTPException(status_code=401, detail=GENERIC_ERROR)

    # Success — reset lockout tracking, issue a new session.
    user.failed_attempts = 0
    user.locked_until = None

    raw_token = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_HOURS),
    )
    db.add(session)
    db.commit()

    return LoginResponse(
        token=raw_token,
        user=LoginUserInfo(id=str(user.id), email=user.email),
    )
@router.post("/logout")
def logout(authorization: str = Header(default=None), db: DBSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"message": "Logged out"}

    raw_token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)

    session = db.query(Session).filter(Session.token_hash == token_hash).first()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.utcnow()
        db.commit()

    return {"message": "Logged out"}