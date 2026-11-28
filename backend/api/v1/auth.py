from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.api import deps
from backend.core import security
from backend.core.config import settings
from backend.models.user import User
from backend.schemas.token import Token

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # 永久有效（ACCESS_TOKEN_EXPIRE_MINUTES=0）时不传过期时间
    access_token_expires = (
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        else None
    )
    return {
        "access_token": security.create_access_token(
            user.id,
            expires_delta=access_token_expires,
            token_version=user.token_version or 0,
        ),
        "token_type": "bearer",
    }
