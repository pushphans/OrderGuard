from datetime import datetime
from decimal import Decimal
import uuid
from pydantic import Field
from pydantic import BaseModel


class CreateProductRequestSchema(BaseModel):
    name : str = Field(..., min_length=2, max_length=80)
    description : str | None = Field(default=None, max_length=500)
    price : Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    stock_quantity : int = Field(..., ge=0, le=10000)


class UpdateProductRequestSchema(BaseModel):
    name : str = Field(..., min_length=2, max_length=80)
    description : str | None = Field(default=None, max_length=500)
    price : Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    stock_quantity : int = Field(..., ge=0, le=10000)


class ProductResponseSchema(BaseModel):
    product_id : uuid.UUID
    user_id : uuid.UUID
    name : str
    description : str | None
    price : Decimal
    stock_quantity : int
    created_at : datetime
    updated_at : datetime
