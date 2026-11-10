import uuid
from orderguard.core.errors import StockLimitExceededError
from orderguard.cart.service.cart_service import add_to_cart
from orderguard.cart.service.cart_service import list_cart
from orderguard.cart.service.cart_service import update_cart_item_quantity
from orderguard.cart.service.cart_service import remove_cart_item
from orderguard.cart.schema.cart_schema import AddCartItemRequestSchema
from orderguard.cart.schema.cart_schema import UpdateCartItemQuantitySchema
from orderguard.auth.utils.current_user_utils import get_user
from orderguard.auth.model.user_model import UserModel
from orderguard.core.db import get_db
from orderguard.core.limiter import limiter
from fastapi import Depends
from fastapi import Request
from fastapi import status
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter


cart_router = APIRouter(prefix="/cart", tags=["CART"])


@cart_router.get("")
@limiter.limit("60/minute")
async def execute_list_cart(
    request: Request,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await list_cart(
            db=db,
            user_id=user.id
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@cart_router.post("/items")
@limiter.limit("20/minute")
async def execute_add_to_cart(
    request: Request,
    data : AddCartItemRequestSchema,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await add_to_cart(
            db=db,
            user_id=user.id,
            data=data
        )

        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Product not found"
        )

    except StockLimitExceededError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Quantity exceeds available stock"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@cart_router.patch("/items/{item_id}")
@limiter.limit("20/minute")
async def execute_update_cart_item_quantity(
    request: Request,
    item_id : uuid.UUID,
    data : UpdateCartItemQuantitySchema,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await update_cart_item_quantity(
            db=db,
            user_id=user.id,
            item_id=item_id,
            data=data
        )

        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Cart item not found"
        )

    except StockLimitExceededError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Quantity exceeds available stock"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@cart_router.delete("/items/{item_id}")
@limiter.limit("20/minute")
async def execute_remove_cart_item(
    request: Request,
    item_id : uuid.UUID,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await remove_cart_item(
            db=db,
            user_id=user.id,
            item_id=item_id
        )

        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Cart item not found"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )
