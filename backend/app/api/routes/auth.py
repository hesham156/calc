from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models import User
from app.schemas import TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: UserRegister, request: Request, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "Email already registered")
    count = db.scalar(select(func.count(User.id))) or 0
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="admin" if count == 0 else "viewer",  # first user becomes admin
    )
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_access_token(user.email, user.role))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return TokenOut(access_token=create_access_token(user.email, user.role))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
