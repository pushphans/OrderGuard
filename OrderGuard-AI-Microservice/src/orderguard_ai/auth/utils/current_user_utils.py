import uuid

from orderguard_ai.auth.utils.jwt_utils import decode_token
from orderguard_ai.core.errors import InvalidTokenError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends

security = HTTPBearer(auto_error=False)


def get_user(
    credentials : HTTPAuthorizationCredentials = Depends(security)
) -> uuid.UUID:
    """Resolve the caller's user id from a JWT issued by the main backend.

    The AI microservice shares the main backend's signing secret, so it can
    verify its access tokens directly. The user id is then used for
    ownership checks / persistence on cart and order rows.
    """

    if credentials is None:
        raise InvalidTokenError("Missing bearer token")

    payload = decode_token(credentials.credentials)

    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError("Token has no subject")

    try:
        return uuid.UUID(user_id)
    except (ValueError, TypeError) as error:
        raise InvalidTokenError("Token subject is not a valid user id") from error
