"""
Key service for handling public key operations
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.database.Message_database import (
    save_public_key,
    get_public_key
)
from app.models.schemas import KeyExchangeRequest, KeyExchangeResponse, PublicKeyResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeyService:
    """Service for handling public key operations"""
    
    @staticmethod
    async def exchange_public_key(request: KeyExchangeRequest) -> KeyExchangeResponse:
        """Exchange public key for a user"""
        try:
            logger.info(f"Exchanging public key for user: {request.did}")
            
            # Save public key to database
            await save_public_key(request.did, request.public_key)
            
            response = KeyExchangeResponse(
                status="success",
                message="Public key saved successfully",
                did=request.did,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"Public key exchanged successfully for user: {request.did}")
            return response
            
        except Exception as e:
            logger.error(f"Error exchanging public key for user {request.did}: {str(e)}")
            raise
    
    @staticmethod
    async def get_user_public_key(did: str) -> PublicKeyResponse:
        """Get public key for a specific user"""
        try:
            logger.info(f"Retrieving public key for user: {did}")
            
            # Get public key from database
            public_key = await get_public_key(did)
            
            if not public_key:
                logger.warning(f"Public key not found for user: {did}")
                raise ValueError(f"Public key not found for user: {did}")
            
            response = PublicKeyResponse(
                did=did,
                public_key=public_key,
                last_updated=datetime.utcnow()  # We'll update this to use DB field
            )
            
            logger.info(f"Public key retrieved successfully for user: {did}")
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving public key for user {did}: {str(e)}")
            raise
