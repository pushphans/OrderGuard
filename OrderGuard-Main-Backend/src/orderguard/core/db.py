from orderguard.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass



engine = create_async_engine(
    url=settings.DATABASE_URL,
    pool_pre_ping=True
)



session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    async with session_factory() as session:
        yield session
