import uuid

from orderguard.products.service.product_service import decrement_stock_batch
from orderguard.internal.schema.internal_schema import DecrementStockRequest
from orderguard.internal.schema.internal_schema import DecrementStockResult
from orderguard.internal.schema.internal_schema import DecrementStockResponse
from orderguard.core.db import get_db
from orderguard.core.config import settings
from orderguard.core.limiter import limiter
from orderguard.core.errors import InsufficientStockError
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi import status
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter


internal_router = APIRouter(prefix="/internal", tags=["INTERNAL"])


async def require_service_token(
    x_service_token : str | None = Header(default=None, alias="X-Service-Token")
):
    if not x_service_token or x_service_token != settings.SERVICE_SECRET:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Invalid service token"
        )



@internal_router.post("/products/decrement-stock")
@limiter.limit("60/minute")
async def execute_decrement_stock(
    request: Request,
    data : DecrementStockRequest,
    db : AsyncSession = Depends(get_db),
    _ : None = Depends(require_service_token)
):
    try:
        items : list[tuple[uuid.UUID, int]] = [
            (item.product_id, item.quantity)
            for item in data.items
        ]

        results = await decrement_stock_batch(db=db, items=items)

        return DecrementStockResponse(
            results=[
                DecrementStockResult(
                    product_id=entry["product_id"],
                    new_stock=entry["new_stock"]
                )
                for entry in results
            ]
        )

    except LookupError:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Product not found"
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
