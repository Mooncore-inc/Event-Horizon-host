"""
Authentication utilities for Event Horizon Chat
"""
import jwt
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from fastapi import HTTPException, WebSocket
import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthManager:
    """Manages authentication for WebSocket connections"""
    
    def __init__(self):
        self.revoked_tokens: Set[str] = set()
        self.token_blacklist: Set[str] = set()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._rotation_task: Optional[asyncio.Task] = None
        
        # Key rotation management
        self.current_secret_key: str = settings.SECRET_KEY
        self.previous_secret_keys: Set[str] = set()
        self.last_rotation: datetime = datetime.utcnow()
        self.rotation_interval: int = settings.KEY_ROTATION_INTERVAL_HOURS * 60 * 60  # From config
        
        self._start_cleanup_task()
        self._start_key_rotation_task()
    
    def _generate_new_secret_key(self) -> str:
        """Generate a new cryptographically secure secret key"""
        return secrets.token_urlsafe(64)
    
    def _rotate_secret_key(self):
        """Rotate the secret key"""
        try:
            # Move current key to previous keys set
            self.previous_secret_keys.add(self.current_secret_key)
            
            # Generate new key
            new_key = self._generate_new_secret_key()
            self.current_secret_key = new_key
            self.last_rotation = datetime.utcnow()
            
            # Keep only last N keys for backward compatibility (from config)
            if len(self.previous_secret_keys) > settings.MAX_PREVIOUS_KEYS:
                oldest_key = min(self.previous_secret_keys, key=lambda k: k)
                self.previous_secret_keys.discard(oldest_key)
            
            logger.info(f"Secret key rotated successfully. New rotation scheduled for {self.last_rotation + timedelta(seconds=self.rotation_interval)}")
            
            # Clear all active tokens to force re-authentication
            self.revoked_tokens.clear()
            self.token_blacklist.clear()
            
        except Exception as e:
            logger.error(f"Error rotating secret key: {e}")
    
    def _start_key_rotation_task(self):
        """Start automatic key rotation task"""
        if not self._rotation_task or self._rotation_task.done():
            self._rotation_task = asyncio.create_task(self._periodic_key_rotation())
    
    async def _periodic_key_rotation(self):
        """Periodic key rotation task"""
        while True:
            try:
                # Wait until next rotation time
                next_rotation = self.last_rotation + timedelta(seconds=self.rotation_interval)
                wait_time = (next_rotation - datetime.utcnow()).total_seconds()
                
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                # Rotate the key
                self._rotate_secret_key()
                
            except Exception as e:
                logger.error(f"Error in key rotation task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    def get_current_secret_key(self) -> str:
        """Get current secret key"""
        return self.current_secret_key
    
    def get_previous_secret_keys(self) -> Set[str]:
        """Get previous secret keys for backward compatibility"""
        return self.previous_secret_keys.copy()
    
    def get_key_rotation_info(self) -> Dict[str, Any]:
        """Get information about key rotation"""
        next_rotation = self.last_rotation + timedelta(seconds=self.rotation_interval)
        return {
            "current_key_hash": hashlib.sha256(self.current_secret_key.encode()).hexdigest()[:16],
            "last_rotation": self.last_rotation.isoformat(),
            "next_rotation": next_rotation.isoformat(),
            "rotation_interval_hours": self.rotation_interval // 3600,
            "previous_keys_count": len(self.previous_secret_keys),
            "total_keys_managed": len(self.previous_secret_keys) + 1
        }
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Add additional security claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),  # Issued at
            "jti": f"token_{hashlib.md5(f'{data.get("did")}_{datetime.utcnow().timestamp()}'.encode()).hexdigest()}",  # JWT ID
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.current_secret_key, algorithm="HS256")
        return encoded_jwt
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT access token with multiple key support"""
        try:
            # Check if token is blacklisted
            if token in self.token_blacklist:
                logger.warning("Token is blacklisted")
                return None
            
            # Check if token is revoked
            if token in self.revoked_tokens:
                logger.warning("Token is revoked")
                return None
            
            # Try current key first
            try:
                payload = jwt.decode(token, self.current_secret_key, algorithms=["HS256"])
                return self._validate_token_payload(payload)
            except jwt.InvalidTokenError:
                pass
            
            # Try previous keys for backward compatibility
            for prev_key in self.previous_secret_keys:
                try:
                    payload = jwt.decode(token, prev_key, algorithms=["HS256"])
                    logger.info("Token verified with previous secret key")
                    return self._validate_token_payload(payload)
                except jwt.InvalidTokenError:
                    continue
            
            logger.warning("Token verification failed with all keys")
            return None
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def _validate_token_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate token payload"""
        try:
            # Additional security checks
            if payload.get("type") != "access":
                logger.warning("Invalid token type")
                return None
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                logger.warning("Token has expired")
                return None
            
            return payload
            
        except Exception as e:
            logger.error(f"Token payload validation error: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a specific token"""
        try:
            # Decode token to get expiration time (try all keys)
            payload = None
            try:
                payload = jwt.decode(token, self.current_secret_key, algorithms=["HS256"], options={"verify_exp": False})
            except jwt.InvalidTokenError:
                for prev_key in self.previous_secret_keys:
                    try:
                        payload = jwt.decode(token, prev_key, algorithms=["HS256"], options={"verify_exp": False})
                        break
                    except jwt.InvalidTokenError:
                        continue
            
            if not payload:
                logger.warning("Cannot revoke invalid token")
                return False
            
            exp_timestamp = payload.get("exp", 0)
            
            # Add to revoked tokens
            self.revoked_tokens.add(token)
            
            # Schedule cleanup after expiration
            asyncio.create_task(self._schedule_token_cleanup(token, exp_timestamp))
            
            logger.info(f"Token revoked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist (permanent)"""
        try:
            self.token_blacklist.add(token)
            logger.info(f"Token added to blacklist")
            return True
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
            return False
    
    async def _schedule_token_cleanup(self, token: str, exp_timestamp: int):
        """Schedule token cleanup after expiration"""
        try:
            exp_time = datetime.fromtimestamp(exp_timestamp)
            wait_time = (exp_time - datetime.utcnow()).total_seconds()
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.revoked_tokens.discard(token)
                logger.debug(f"Expired token {token[:10]}... cleaned up")
        except Exception as e:
            logger.error(f"Error in token cleanup: {e}")
    
    def _start_cleanup_task(self):
        """Start periodic cleanup task"""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired tokens"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                current_time = datetime.utcnow()
                
                # Clean up expired tokens from revoked list
                expired_tokens = set()
                for token in self.revoked_tokens:
                    try:
                        # Try to decode with current key
                        payload = jwt.decode(token, self.current_secret_key, algorithms=["HS256"], options={"verify_exp": False})
                        if current_time > datetime.fromtimestamp(payload["exp"]):
                            expired_tokens.add(token)
                    except:
                        # If can't decode, consider it expired
                        expired_tokens.add(token)
                
                self.revoked_tokens -= expired_tokens
                if expired_tokens:
                    logger.debug(f"Cleaned up {len(expired_tokens)} expired tokens")
                    
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    @staticmethod
    def create_did_signature(did: str, timestamp: str, secret: str) -> str:
        """Create HMAC signature for DID verification"""
        message = f"{did}:{timestamp}"
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def verify_did_signature(did: str, timestamp: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature for DID"""
        expected_signature = AuthManager.create_did_signature(did, timestamp, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    async def authenticate_websocket(
        self, 
        websocket: WebSocket, 
        did: str, 
        token: Optional[str] = None,
        signature: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> bool:
        """Authenticate WebSocket connection"""
        try:
            # Validate DID format
            if not did.startswith('did:'):
                logger.warning(f"Invalid DID format: {did}")
                return False
            
            # Check if token is provided
            if token:
                # Verify JWT token with enhanced security
                payload = self.verify_access_token(token)
                if not payload:
                    logger.warning(f"Invalid JWT token for DID: {did}")
                    return False
                
                # Check if DID matches token
                if payload.get("did") != did:
                    logger.warning(f"DID mismatch in token for: {did}")
                    return False
                
                logger.info(f"JWT authentication successful for DID: {did}")
                return True
            
            # Check if signature is provided (alternative authentication method)
            elif signature and timestamp:
                # Verify timestamp is not too old (within 5 minutes)
                try:
                    ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if datetime.utcnow() - ts > timedelta(minutes=5):
                        logger.warning(f"Signature timestamp too old for DID: {did}")
                        return False
                except ValueError:
                    logger.warning(f"Invalid timestamp format for DID: {did}")
                    return False
                
                # Verify signature using current secret key
                if self.verify_did_signature(did, timestamp, signature, self.current_secret_key):
                    logger.info(f"Signature authentication successful for DID: {did}")
                    return True
                else:
                    logger.warning(f"Invalid signature for DID: {did}")
                    return False
            
            # For development, allow connections without authentication
            elif settings.DEBUG:
                logger.info(f"Development mode: allowing unauthenticated connection for DID: {did}")
                return True
            
            else:
                logger.warning(f"No authentication provided for DID: {did}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error for DID {did}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._rotation_task and not self._rotation_task.done():
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass


# Global auth manager instance
auth_manager = AuthManager()
