from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_async_engine(settings.DB_DSN, pool_pre_ping=True, future=True)
async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
