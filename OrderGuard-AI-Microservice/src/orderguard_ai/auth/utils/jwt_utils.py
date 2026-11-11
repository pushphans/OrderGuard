from orderguard_ai.core.config import settings
from orderguard_ai.core.errors import InvalidTokenError
import jwt


def decode_token(token : str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except jwt.PyJWTError as error:
        raise InvalidTokenError(str(error)) from error

    return payload
