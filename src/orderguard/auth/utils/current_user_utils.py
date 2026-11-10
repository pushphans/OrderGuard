from orderguard.auth.model.user_model import UserModel
from sqlalchemy import select
from orderguard.auth.utils.jwt_utils import decode_token
from sqlalchemy.ext.asyncio import AsyncSession
from orderguard.core.db import get_db
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends

security = HTTPBearer(auto_error=False)

class InvalidTokenError(Exception):
    pass

class InvalidCredentialError(Exception):
    pass



async def get_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db : AsyncSession = Depends(get_db)
):

    if credentials is None:
        raise InvalidTokenError

    token = credentials.credentials

    payload = await decode_token(token=token)

    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidCredentialError

    query = (
        select(UserModel)
        .where(UserModel.id == user_id)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialError

    return user
