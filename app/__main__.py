from datetime import datetime
from typing import List, Optional
import uvicorn
import os
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.database.Message_database import (
    save_public_key,
    get_public_key,
    save_private_message,
    get_private_messages
)
from app.database.database import init_db

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections[username] = websocket

    async def disconnect(self, username: str):
        async with self.lock:
            if username in self.active_connections:
                del self.active_connections[username]

    async def send_personal_message(self, message: dict, username: str):
        async with self.lock:
            connection = self.active_connections.get(username)
        if connection:
            await connection.send_json(message)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    await init_db()

class KeyExchangeRequest(BaseModel):
    did: str = Field(..., min_length=5, max_length=255)
    public_key: str

class PrivateMessageRequest(BaseModel):
    sender_did: str = Field(..., min_length=5, max_length=255)
    recipient_did: str = Field(..., min_length=5, max_length=255)
    encrypted_key: str
    iv: str
    ciphertext: str

class PrivateMessageResponse(BaseModel):
    id: str
    sender_did: str
    recipient_did: str
    encrypted_key: str
    iv: str
    ciphertext: str
    timestamp: datetime

@app.post("/exchange_keys")
async def exchange_keys(request: KeyExchangeRequest):
    await save_public_key(request.did, request.public_key)
    return {"status": "success"}

@app.get("/public_key/{did}")
async def get_user_public_key(did: str):
    key = await get_public_key(did)
    if not key:
        raise HTTPException(404, detail="Public key not found")
    return {"public_key": key}

@app.post("/send_private", response_model=PrivateMessageResponse)
async def send_private_message(message: PrivateMessageRequest):
    new_message = await save_private_message(
        sender_did=message.sender_did,
        recipient_did=message.recipient_did,
        encrypted_key=message.encrypted_key,
        iv=message.iv,
        ciphertext=message.ciphertext
    )

    await manager.send_personal_message(
        {
            "type": "private_message",
            "sender_did": message.sender_did,
            "recipient_did": message.recipient_did,
            "encrypted_key": message.encrypted_key,
            "iv": message.iv,
            "ciphertext": message.ciphertext,
            "timestamp": new_message["timestamp"].isoformat()
        },
        message.recipient_did
    )
    
    return {**new_message, **message.dict()}

@app.get("/private_messages/{did}", response_model=List[PrivateMessageResponse])
async def get_private_messages_endpoint(
    did: str,
    limit: Optional[int] = 100
):
    safe_limit = min(max(1, limit or 100), 1000)
    messages = await get_private_messages(did, safe_limit)
    return messages

@app.websocket("/ws/{did}")
async def websocket_endpoint(websocket: WebSocket, did: str):
    await manager.connect(did, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(did)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)