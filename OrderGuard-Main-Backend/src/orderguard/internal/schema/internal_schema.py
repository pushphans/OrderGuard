import uuid
from pydantic import BaseModel
from pydantic import Field


class DecrementStockItem(BaseModel):
    product_id : uuid.UUID
    quantity : int = Field(..., ge=1)


class DecrementStockRequest(BaseModel):
    items : list[DecrementStockItem]


class DecrementStockResult(BaseModel):
    product_id : uuid.UUID
    new_stock : int


class DecrementStockResponse(BaseModel):
    results : list[DecrementStockResult]
