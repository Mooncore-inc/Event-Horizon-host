"""
WebSocket endpoints for real-time messaging
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.websocket.manager import manager
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/{did}")
async def websocket_endpoint(
    websocket: WebSocket, 
    did: str,
    token: Optional[str] = Query(None, description="Authentication token"),
    signature: Optional[str] = Query(None, description="HMAC signature for authentication"),
    timestamp: Optional[str] = Query(None, description="Timestamp for signature validation")
):
    """WebSocket endpoint for real-time messaging"""
    try:
        # Authenticate the connection
        from app.core.auth import auth_manager
        is_authenticated = await auth_manager.authenticate_websocket(
            websocket, did, token, signature, timestamp
        )
        
        if not is_authenticated:
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Connect to WebSocket
        success = await manager.connect(did, websocket)
        if not success:
            await websocket.close(code=1011, reason="Connection failed")
            return
        
        logger.info(f"WebSocket connection established for {did}")
        
        try:
            # Main message loop
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "unknown")
                    
                    logger.debug(f"Received {message_type} message from {did}")
                    
                    # Handle different message types
                    if message_type == "heartbeat":
                        # Update last heartbeat
                        await manager._update_heartbeat(did)
                        
                    elif message_type == "ping":
                        # Respond to ping
                        pong_msg = {
                            "type": "pong",
                            "data": {
                                "timestamp": message.get("data", {}).get("timestamp")
                            }
                        }
                        await websocket.send_json(pong_msg)
                        
                    elif message_type == "status":
                        # Send connection status
                        status_msg = {
                            "type": "status",
                            "data": {
                                "connected": True,
                                "did": did,
                                "timestamp": message.get("data", {}).get("timestamp")
                            }
                        }
                        await websocket.send_json(status_msg)
                        
                    else:
                        # Echo back unknown message types
                        echo_msg = {
                            "type": "echo",
                            "data": message.get("data", {}),
                            "timestamp": message.get("timestamp")
                        }
                        await websocket.send_json(echo_msg)
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from {did}")
                    error_msg = {
                        "type": "error",
                        "data": {
                            "message": "Invalid JSON format",
                            "timestamp": None
                        }
                    }
                    await websocket.send_json(error_msg)
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for {did}")
            
        except Exception as e:
            logger.error(f"Error in WebSocket loop for {did}: {e}")
            try:
                await websocket.close(code=1011, reason="Internal error")
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error establishing WebSocket connection for {did}: {e}")
        try:
            await websocket.close(code=1011, reason="Connection error")
        except:
            pass
    
    finally:
        # Always disconnect when done
        await manager.disconnect(did)


@router.get("/connections/status")
async def get_connection_status():
    """Get current connection status"""
    try:
        connected_users = await manager.get_connected_users()
        connection_count = await manager.get_connection_count()
        
        return {
            "total_connections": connection_count,
            "connected_users": list(connected_users),
            "status": "active"
        }
        
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise


@router.get("/connections/{did}")
async def get_user_connection_info(did: str):
    """Get connection information for a specific user"""
    try:
        connection_info = await manager.get_connection_info(did)
        
        if not connection_info:
            return {
                "did": did,
                "connected": False,
                "message": "User not connected"
            }
        
        return {
            "did": did,
            "connected": True,
            "connection_info": connection_info
        }
        
    except Exception as e:
        logger.error(f"Error getting connection info for {did}: {e}")
        raise
