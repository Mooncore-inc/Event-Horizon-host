"""
Pydantic schemas for API requests and responses
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class KeyExchangeRequest(BaseModel):
    """Request model for public key exchange"""
    did: str = Field(..., min_length=5, max_length=255, description="User's Decentralized Identifier")
    public_key: str = Field(..., description="User's public key for encryption")
    
    @validator('did')
    def validate_did(cls, v):
        if not v.startswith('did:'):
            raise ValueError('DID must start with "did:"')
        return v


class KeyExchangeResponse(BaseModel):
    """Response model for public key exchange"""
    status: str = "success"
    message: str = "Public key saved successfully"
    did: str
    timestamp: datetime


class PublicKeyResponse(BaseModel):
    """Response model for public key retrieval"""
    did: str
    public_key: str
    last_updated: Optional[datetime] = None


class PrivateMessageRequest(BaseModel):
    """Request model for sending private messages"""
    sender_did: str = Field(..., min_length=5, max_length=255, description="Sender's DID")
    recipient_did: str = Field(..., min_length=5, max_length=255, description="Recipient's DID")
    encrypted_key: str = Field(..., description="Encrypted symmetric key")
    iv: str = Field(..., description="Initialization vector")
    ciphertext: str = Field(..., description="Encrypted message content")
    
    @validator('sender_did', 'recipient_did')
    def validate_dids(cls, v):
        if not v.startswith('did:'):
            raise ValueError('DID must start with "did:"')
        return v


class PrivateMessageResponse(BaseModel):
    """Response model for private messages"""
    id: str
    sender_did: str
    recipient_did: str
    encrypted_key: str
    iv: str
    ciphertext: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Response model for message list"""
    messages: List[PrivateMessageResponse]
    total: int
    limit: int
    offset: int


class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str = Field(..., description="Message type")
    data: dict = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    database: str = "connected"
