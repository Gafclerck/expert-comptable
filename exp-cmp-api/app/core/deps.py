from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import session
from app.modules.identity.models import User, UserStatus
from app.modules.identity.service import get_user_from_token, is_root

limiter = Limiter(key_func=get_remote_address)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_STR}/auth/login"
)


def get_session() -> Generator[Session, None, None]:
    db = session()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)],
    db: Annotated[Session, Depends(get_session)],
) -> User:
    user = get_user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte inactif",
        )
    return current_user


def require_root(current_user: User = Depends(get_current_active_user)) -> User:
    if not is_root(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve au ROOT",
        )
    return current_user


SessionDep = Annotated[Session, Depends(get_session)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
RequireRoot = Annotated[User, Depends(require_root)]