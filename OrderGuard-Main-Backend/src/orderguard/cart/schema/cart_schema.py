from datetime import datetime
from decimal import Decimal
import uuid
from pydantic import Field
from pydantic import BaseModel


class AddCartItemRequestSchema(BaseModel):
    product_id : uuid.UUID
    quantity : int = Field(..., ge=1, le=100)


class UpdateCartItemQuantitySchema(BaseModel):
    quantity : int = Field(..., ge=1, le=100)


class CartItemResponseSchema(BaseModel):
    item_id : uuid.UUID
    product_id : uuid.UUID
    name : str
    price : Decimal
    quantity : int
    line_total : Decimal
    created_at : datetime
