import uuid
from orderguard.core.errors import CartEmptyError
from orderguard.core.errors import InsufficientStockError
from orderguard.orders.service.order_service import place_order
from orderguard.orders.service.order_service import get_order
from orderguard.orders.service.order_service import list_orders
from orderguard.auth.utils.current_user_utils import get_user
from orderguard.auth.model.user_model import UserModel
from orderguard.core.db import get_db
from orderguard.core.limiter import limiter
from fastapi import Depends
from fastapi import Request
from fastapi import Query
from fastapi import status
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter


order_router = APIRouter(prefix="/orders", tags=["ORDERS"])


@order_router.post("")
@limiter.limit("10/minute")
async def execute_place_order(
    request: Request,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await place_order(
            db=db,
            user_id=user.id
        )

        return result

    except CartEmptyError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Cart is empty"
        )

    except InsufficientStockError:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = "Insufficient stock for one or more items"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@order_router.get("")
@limiter.limit("60/minute")
async def execute_list_orders(
    request: Request,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user),
    page_number : int = Query(default=1, ge=1),
    page_size : int = Query(default=10, le=100)
):
    try:
        result = await list_orders(
            db=db,
            user_id=user.id,
            page_number=page_number,
            page_size=page_size
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@order_router.get("/{order_id}")
@limiter.limit("60/minute")
async def execute_get_order(
    request: Request,
    order_id : uuid.UUID,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await get_order(
            db=db,
            user_id=user.id,
            order_id=order_id
        )

        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Not found"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )
