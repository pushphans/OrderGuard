from datetime import datetime
from decimal import Decimal
import uuid
from orderguard.core.enums import OrderStatus
from pydantic import BaseModel


class OrderItemResponseSchema(BaseModel):
    product_id : uuid.UUID
    name : str
    price : Decimal
    quantity : int
    line_total : Decimal


class OrderResponseSchema(BaseModel):
    order_id : uuid.UUID
    user_id : uuid.UUID
    status : OrderStatus
    total_price : Decimal
    created_at : datetime
    updated_at : datetime
    items : list[OrderItemResponseSchema]
