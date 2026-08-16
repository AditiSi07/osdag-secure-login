from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from passlib.context import CryptContext

from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, RegisterResponse

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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