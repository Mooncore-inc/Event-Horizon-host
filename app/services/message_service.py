"""
Message service for handling private messages
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from app.database.Message_database import (
    save_private_message,
    get_private_messages
)
from app.models.schemas import PrivateMessageRequest, PrivateMessageResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class MessageService:
    """Service for handling message operations"""
    
    @staticmethod
    async def send_private_message(message: PrivateMessageRequest) -> Dict[str, Any]:
        """Send a private message"""
        try:
            logger.info(f"Sending message from {message.sender_did} to {message.recipient_did}")
            
            # Save message to database
            saved_message = await save_private_message(
                sender_did=message.sender_did,
                recipient_did=message.recipient_did,
                encrypted_key=message.encrypted_key,
                iv=message.iv,
                ciphertext=message.ciphertext
            )
            
            # Prepare response
            response_data = {
                "id": saved_message["id"],
                "sender_did": message.sender_did,
                "recipient_did": message.recipient_did,
                "encrypted_key": message.encrypted_key,
                "iv": message.iv,
                ciphertext=message.ciphertext,
                "timestamp": saved_message["timestamp"]
            }
            
            logger.info(f"Message sent successfully with ID: {saved_message['id']}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise
    
    @staticmethod
    async def get_user_messages(
        did: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get messages for a specific user"""
        try:
            logger.info(f"Fetching messages for user: {did}")
            
            # Get messages from database
            messages = await get_private_messages(did, limit + offset)
            
            # Apply offset
            if offset > 0:
                messages = messages[offset:]
            
            # Apply limit
            messages = messages[:limit]
            
            # Convert to response format
            message_responses = []
            for msg in messages:
                message_responses.append(PrivateMessageResponse(
                    id=msg["id"],
                    sender_did=msg["sender_did"],
                    recipient_did=msg["recipient_did"],
                    encrypted_key=msg["encrypted_key"],
                    iv=msg["iv"],
                    ciphertext=msg["ciphertext"],
                    timestamp=msg["timestamp"]
                ))
            
            response = {
                "messages": message_responses,
                "total": len(message_responses),
                "limit": limit,
                "offset": offset
            }
            
            logger.info(f"Retrieved {len(message_responses)} messages for user: {did}")
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving messages for user {did}: {str(e)}")
            raise
