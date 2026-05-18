from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.security import issue_jwt, verify_password
from src.models.users import User


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def make_token_for(user: User) -> tuple[str, int]:
    return issue_jwt(str(user.user_id))
