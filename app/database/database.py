import logging
import os

from sqlalchemy import Column, DateTime, Text, String, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from datetime import datetime

logger = logging.getLogger(__name__)

# Async Database Engine configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./database.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class PublicKey(Base):
    __tablename__ = "public_keys"
    username = Column(String(50), primary_key=True)
    public_key = Column(Text, nullable=False)

class PrivateMessage(Base):
    __tablename__ = "private_messages"
    id = Column(String(36), primary_key=True)
    sender = Column(String(50), nullable=False)
    recipient = Column(String(50), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    iv = Column(Text, nullable=False)
    ciphertext = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)