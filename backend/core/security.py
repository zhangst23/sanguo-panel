from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from backend.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    token_version: int = 0,
) -> str:
    # ACCESS_TOKEN_EXPIRE_MINUTES 为 0 时不写 exp，Token 永久有效
    if expires_delta is None and settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(subject), "token_ver": int(token_version or 0)}
    if expires_delta:
        to_encode["exp"] = datetime.utcnow() + expires_delta
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
