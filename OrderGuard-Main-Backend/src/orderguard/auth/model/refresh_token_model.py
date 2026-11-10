from sqlalchemy import ForeignKey
from datetime import datetime
from sqlalchemy import UUID, Text, DateTime, func
import uuid
from sqlalchemy.orm import mapped_column, Mapped
from orderguard.core.db import Base



class RefreshTokenModel(Base):
    __tablename__ = "refresh_token"

    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, nullable = False, default = uuid.uuid4)
    refresh_token : Mapped[str] = mapped_column(Text, nullable = False)
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable = False, index = True)
    refresh_token_expiry : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable = False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default = func.now(), nullable = False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default = func.now(), onupdate = func.now(), nullable = False)
