from orderguard.core.errors import RefreshTokenExpired
from orderguard.auth.utils.current_user_utils import InvalidCredentialError
from orderguard.core.errors import UserAlreadyExistsError
from orderguard.core.errors import IncompleteCredentialsError
from orderguard.auth.services.auth_service import refresh_token
from orderguard.auth.schema.auth_schemas import RefreshTokenRequestModel
from orderguard.auth.services.auth_service import login
from orderguard.auth.schema.auth_schemas import LoginRequestModel
from orderguard.auth.services.auth_service import register
from fastapi import status
from fastapi import Request
from fastapi import HTTPException
from orderguard.auth.schema.auth_schemas import RegisterRequestModel
from orderguard.auth.utils.current_user_utils import get_user
from orderguard.auth.model.user_model import UserModel
from orderguard.core.db import get_db
from orderguard.core.limiter import limiter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter


auth_router = APIRouter(prefix="/auth", tags = ["AUTH"])



@auth_router.post("/register")
@limiter.limit("10/minute")
async def execute_register(
    request: Request,
    data : RegisterRequestModel,
    db : AsyncSession = Depends(get_db),
):
    try:
        result = await register(data=data, db=db)
        return result

    except IncompleteCredentialsError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Invalid input"
        )

    except UserAlreadyExistsError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "User already exists"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )



@auth_router.post("/login")
@limiter.limit("10/minute")
async def execute_login(
    request: Request,
    data : LoginRequestModel,
    db : AsyncSession = Depends(get_db),
):
    try:
        result = await login(data=data, db=db)
        return result

    except IncompleteCredentialsError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Invalid input"
        )


    except InvalidCredentialError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Invalid credentials"
        )


    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@auth_router.post("/refresh-token")
@limiter.limit("10/minute")
async def execute_refresh_token(
    request: Request,
    data : RefreshTokenRequestModel,
    db : AsyncSession = Depends(get_db),
):
    try:
        result = await refresh_token(db=db, data=data)
        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "No token found"
        )

    except RefreshTokenExpired:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Refresh token expired, login again"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )
