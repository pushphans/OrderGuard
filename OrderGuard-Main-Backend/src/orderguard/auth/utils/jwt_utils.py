import secrets
import jwt
from orderguard.core.config import settings
from datetime import timedelta
from datetime import timezone
from datetime import datetime
import uuid



async def create_access_token(user_id : uuid.UUID):
    payload= {
        "sub" : str(user_id),
        "exp" : datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRY_IN_MINUTES)
    }

    encoded_token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_token


async def decode_token(token : str):
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )

    return payload



async def create_refresh_token():
    return secrets.token_urlsafe(64)
