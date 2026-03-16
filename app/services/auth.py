from typing import Optional

from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def create_user(db: Session, email: str, password: str, full_name: Optional[str]) -> User:
    user = User(
        email=email.lower().strip(),
        full_name=full_name.strip() if full_name else None,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
