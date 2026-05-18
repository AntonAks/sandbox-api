from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.security import decode_jwt
from src.db import get_session
from src.models.users import User

_bearer = HTTPBearer(auto_error=True)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
BearerDep = Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]


async def get_current_user(credentials: BearerDep, session: SessionDep) -> User:
    token = credentials.credentials
    try:
        payload = decode_jwt(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await session.execute(select(User).where(User.user_id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
