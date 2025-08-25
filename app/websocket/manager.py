"""
WebSocket connection manager for real-time messaging
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time messaging"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Start heartbeat monitoring
        self._start_heartbeat()
    
    async def connect(self, did: str, websocket: WebSocket) -> bool:
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            
            async with self.lock:
                # Close existing connection if any
                if did in self.active_connections:
                    try:
                        await self.active_connections[did].close()
                    except Exception as e:
                        logger.warning(f"Error closing existing connection for {did}: {e}")
                
                self.active_connections[did] = websocket
                self.connection_metadata[did] = {
                    "connected_at": datetime.utcnow(),
                    "last_heartbeat": datetime.utcnow(),
                    "message_count": 0
                }
                
            logger.info(f"User {did} connected successfully")
            
            # Send welcome message
            await self._send_welcome_message(did)
            
            return True
            
        except Exception as e:
            logger.error(f"Error accepting connection for {did}: {e}")
            return False
    
    async def disconnect(self, did: str) -> bool:
        """Disconnect a user"""
        try:
            async with self.lock:
                if did in self.active_connections:
                    del self.active_connections[did]
                if did in self.connection_metadata:
                    del self.connection_metadata[did]
                    
            logger.info(f"User {did} disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting user {did}: {e}")
            return False
    
    async def send_personal_message(self, message: dict, did: str) -> bool:
        """Send a message to a specific user"""
        try:
            async with self.lock:
                connection = self.active_connections.get(did)
                metadata = self.connection_metadata.get(did)
            
            if connection and metadata:
                # Update message count
                metadata["message_count"] += 1
                
                # Send message
                await connection.send_json(message)
                logger.debug(f"Message sent to {did}: {message.get('type', 'unknown')}")
                return True
            else:
                logger.warning(f"User {did} is not connected")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {did}: {e}")
            # Mark connection as potentially broken
            await self._handle_broken_connection(did)
            return False
    
    async def broadcast_message(self, message: dict, exclude_did: Optional[str] = None) -> int:
        """Broadcast message to all connected users"""
        sent_count = 0
        failed_connections = []
        
        async with self.lock:
            connections_to_send = list(self.active_connections.items())
        
        for did, connection in connections_to_send:
            if exclude_did and did == exclude_did:
                continue
                
            try:
                await connection.send_json(message)
                sent_count += 1
                logger.debug(f"Broadcast message sent to {did}")
                
            except Exception as e:
                logger.error(f"Error broadcasting to {did}: {e}")
                failed_connections.append(did)
        
        # Clean up failed connections
        for failed_did in failed_connections:
            await self._handle_broken_connection(failed_did)
        
        return sent_count
    
    async def get_connection_info(self, did: str) -> Optional[Dict[str, Any]]:
        """Get connection information for a user"""
        async with self.lock:
            if did in self.connection_metadata:
                return self.connection_metadata[did].copy()
        return None
    
    async def get_connected_users(self) -> Set[str]:
        """Get list of currently connected users"""
        async with self.lock:
            return set(self.active_connections.keys())
    
    async def get_connection_count(self) -> int:
        """Get total number of active connections"""
        async with self.lock:
            return len(self.active_connections)
    
    async def _send_welcome_message(self, did: str):
        """Send welcome message to newly connected user"""
        welcome_msg = {
            "type": "welcome",
            "data": {
                "message": "Welcome to Event Horizon Chat!",
                "did": did,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await self.send_personal_message(welcome_msg, did)
    
    async def _handle_broken_connection(self, did: str):
        """Handle broken WebSocket connections"""
        logger.warning(f"Handling broken connection for {did}")
        await self.disconnect(did)
    
    async def _heartbeat_loop(self):
        """Send heartbeat messages to all connections"""
        while True:
            try:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                
                heartbeat_msg = {
                    "type": "heartbeat",
                    "data": {
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                # Send heartbeat to all connections
                await self.broadcast_message(heartbeat_msg)
                
                # Check for stale connections
                await self._cleanup_stale_connections()
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _update_heartbeat(self, did: str):
        """Update heartbeat timestamp for a user"""
        async with self.lock:
            if did in self.connection_metadata:
                self.connection_metadata[did]["last_heartbeat"] = datetime.utcnow()
    
    async def _cleanup_stale_connections(self):
        """Clean up stale connections"""
        current_time = datetime.utcnow()
        stale_connections = []
        
        async with self.lock:
            for did, metadata in self.connection_metadata.items():
                time_since_heartbeat = current_time - metadata["last_heartbeat"]
                if time_since_heartbeat > timedelta(seconds=settings.WS_CONNECTION_TIMEOUT):
                    stale_connections.append(did)
        
        # Disconnect stale connections
        for did in stale_connections:
            logger.info(f"Disconnecting stale connection for {did}")
            await self.disconnect(did)
    
    def _start_heartbeat(self):
        """Start heartbeat monitoring task"""
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Heartbeat monitoring started")
    
    async def stop(self):
        """Stop the connection manager"""
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self.lock:
            for did, connection in self.active_connections.items():
                try:
                    await connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection for {did}: {e}")
        
        logger.info("Connection manager stopped")


# Global connection manager instance
manager = ConnectionManager()
