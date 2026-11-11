import uuid
from orderguard.core.errors import NotOwnerError
from orderguard.products.model.product_model import ProductModel
from orderguard.products.service.product_service import create_product
from orderguard.products.service.product_service import get_product
from orderguard.products.service.product_service import list_products
from orderguard.products.service.product_service import update_product
from orderguard.products.service.product_service import delete_product
from orderguard.products.schema.product_schema import CreateProductRequestSchema
from orderguard.products.schema.product_schema import UpdateProductRequestSchema
from orderguard.products.schema.product_schema import ProductResponseSchema
from orderguard.auth.utils.current_user_utils import get_user
from orderguard.auth.model.user_model import UserModel
from orderguard.core.db import get_db
from orderguard.core.limiter import limiter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import status
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter


product_router = APIRouter(prefix="/products", tags=["PRODUCTS"])


@product_router.get("")
@limiter.limit("60/minute")
async def execute_list_products(
    request: Request,
    db : AsyncSession = Depends(get_db),
    page_number : int = Query(default=1, ge=1),
    page_size : int = Query(default=10, le=100),
    search : str | None = Query(default=None, max_length=80)
):
    try:
        products = await list_products(
            db=db,
            page_number=page_number,
            page_size=page_size,
            search=search
        )

        return [
            ProductResponseSchema(
                product_id=product.id,
                user_id=product.user_id,
                name=product.name,
                description=product.description,
                price=product.price,
                stock_quantity=product.stock_quantity,
                created_at=product.created_at,
                updated_at=product.updated_at
            )
            for product in products
        ]

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@product_router.get("/{product_id}")
@limiter.limit("60/minute")
async def execute_get_product(
    request: Request,
    product_id : uuid.UUID,
    db : AsyncSession = Depends(get_db)
):
    try:
        result = await get_product(
            db=db,
            product_id=product_id
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


@product_router.post("")
@limiter.limit("10/minute")
async def execute_create_product(
    request: Request,
    data : CreateProductRequestSchema,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await create_product(
            user_id=user.id,
            data=data,
            db=db
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@product_router.put("/{product_id}")
@limiter.limit("10/minute")
async def execute_update_product(
    request: Request,
    product_id : uuid.UUID,
    data : UpdateProductRequestSchema,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await update_product(
            db=db,
            user_id=user.id,
            product_id=product_id,
            data=data
        )

        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Not found"
        )

    except NotOwnerError:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "You do not own this product"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )


@product_router.delete("/{product_id}")
@limiter.limit("10/minute")
async def execute_delete_product(
    request: Request,
    product_id : uuid.UUID,
    db : AsyncSession = Depends(get_db),
    user : UserModel = Depends(get_user)
):
    try:
        result = await delete_product(
            db=db,
            user_id=user.id,
            product_id=product_id
        )

        return result

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Not found"
        )

    except NotOwnerError:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "You do not own this product"
        )

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(e)
        )
