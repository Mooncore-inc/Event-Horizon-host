import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy import insert, select, desc, update

from .database import PublicKey, PrivateMessage, async_session

logger = logging.getLogger(__name__)

async def save_public_key(username: str, public_key: str):
    async with async_session() as session:
        async with session.begin():
            existing = await session.get(PublicKey, username)
            if existing:
                stmt = update(PublicKey).where(
                    PublicKey.username == username
                ).values(public_key=public_key)
                await session.execute(stmt)
            else:
                stmt = insert(PublicKey).values(
                    username=username,
                    public_key=public_key
                )
                await session.execute(stmt)

async def get_public_key(username: str) -> str:
    async with async_session() as session:
        result = await session.get(PublicKey, username)
        return result.public_key if result else None

async def save_private_message(
    sender: str,
    recipient: str,
    encrypted_key: str,
    iv: str,
    ciphertext: str
) -> dict:
    async with async_session() as session:
        async with session.begin():
            message_id = str(uuid4())
            timestamp = datetime.utcnow()
            
            stmt = insert(PrivateMessage).values(
                id=message_id,
                sender=sender,
                recipient=recipient,
                encrypted_key=encrypted_key,
                iv=iv,
                ciphertext=ciphertext,
                timestamp=timestamp
            )
            
            await session.execute(stmt)
            return {
                "id": message_id,
                "sender": sender,
                "recipient": recipient,
                "timestamp": timestamp
            }

async def get_private_messages(username: str, limit: int = 100) -> list:
    async with async_session() as session:
        stmt = select(
            PrivateMessage.id,
            PrivateMessage.sender,
            PrivateMessage.recipient,
            PrivateMessage.encrypted_key,
            PrivateMessage.iv,
            PrivateMessage.ciphertext,
            PrivateMessage.timestamp
        ).where(
            (PrivateMessage.sender == username) | 
            (PrivateMessage.recipient == username)
        ).order_by(
            desc(PrivateMessage.timestamp)
        ).limit(limit)
        
        result = await session.execute(stmt)
        return [dict(row) for row in result.mappings()]