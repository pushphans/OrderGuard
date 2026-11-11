from datetime import datetime
from sqlalchemy import UniqueConstraint
import uuid
from sqlalchemy import UUID, Integer, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped
from orderguard_ai.core.db import Base


class CartItemModel(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_cart_items_user_product"),
    )

    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # user + product live in the main backend; stored here as plain UUIDs
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    quantity : Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
