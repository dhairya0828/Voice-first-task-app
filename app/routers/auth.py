from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import TokenResponse, UserRegisterRequest, UserResponse
from app.security import create_access_token
from app.services.auth import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginJSONRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = create_user(db, payload.email, payload.password, payload.full_name)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, expires_in_minutes=settings.access_token_expire_minutes)


@router.post("/login-json", response_model=TokenResponse)
def login_json(payload: LoginJSONRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, expires_in_minutes=settings.access_token_expire_minutes)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user
