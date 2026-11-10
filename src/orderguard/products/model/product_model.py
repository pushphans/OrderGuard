from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from decimal import Decimal
from sqlalchemy import UUID, Text, Integer, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from orderguard.core.db import Base



class ProductModel(Base):
    __tablename__ = "products"

    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key = True, default = uuid.uuid4, nullable = False)
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable = False, index = True)
    name : Mapped[str] = mapped_column(Text, nullable = False)
    description : Mapped[str] = mapped_column(Text)
    price : Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable = False)
    stock_quantity : Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default = func.now(), nullable = False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default = func.now(), onupdate = func.now(), nullable = False)
