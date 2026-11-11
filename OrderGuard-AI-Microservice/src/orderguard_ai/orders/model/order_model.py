from decimal import Decimal
from datetime import datetime
import uuid
from sqlalchemy import ForeignKey
from sqlalchemy import UUID, Text, Integer, Numeric, DateTime, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from orderguard_ai.core.db import Base
from orderguard_ai.core.enums import OrderStatus


class OrderModel(Base):
    __tablename__ = "orders"

    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # user lives in the main backend; stored here as a plain UUID
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status : Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_price : Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=2), nullable=False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    order_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    # product lives in the main backend; stored here as a plain UUID snapshot
    product_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name : Mapped[str] = mapped_column(Text, nullable=False)
    price : Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=2), nullable=False)
    quantity : Mapped[int] = mapped_column(Integer, nullable=False)
    line_total : Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=2), nullable=False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
