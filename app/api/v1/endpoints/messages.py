"""
Message API endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.schemas import (
    PrivateMessageRequest,
    PrivateMessageResponse,
    MessageListResponse,
    ErrorResponse
)
from app.services.message_service import MessageService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/send", response_model=PrivateMessageResponse)
async def send_private_message(message: PrivateMessageRequest):
    """Send a private message"""
    try:
        logger.info(f"Received message request from {message.sender_did} to {message.recipient_did}")
        
        result = await MessageService.send_private_message(message)
        
        return PrivateMessageResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in send_private_message endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{did}", response_model=MessageListResponse)
async def get_user_messages(
    did: str,
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of messages to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of messages to skip")
):
    """Get messages for a specific user"""
    try:
        logger.info(f"Retrieving messages for user: {did}")
        
        result = await MessageService.get_user_messages(did, limit, offset)
        
        return MessageListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in get_user_messages endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{did}/count")
async def get_message_count(did: str):
    """Get message count for a specific user"""
    try:
        logger.info(f"Retrieving message count for user: {did}")
        
        result = await MessageService.get_user_messages(did, 1, 0)
        
        return {
            "did": did,
            "message_count": result["total"]
        }
        
    except Exception as e:
        logger.error(f"Error in get_message_count endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
