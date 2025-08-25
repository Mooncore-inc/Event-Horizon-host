"""
Key management API endpoints
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import (
    KeyExchangeRequest,
    KeyExchangeResponse,
    PublicKeyResponse,
    ErrorResponse
)
from app.services.key_service import KeyService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/exchange", response_model=KeyExchangeResponse)
async def exchange_keys(request: KeyExchangeRequest):
    """Exchange public key for a user"""
    try:
        logger.info(f"Received key exchange request for user: {request.did}")
        
        result = await KeyService.exchange_public_key(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in exchange_keys endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{did}", response_model=PublicKeyResponse)
async def get_user_public_key(did: str):
    """Get public key for a specific user"""
    try:
        logger.info(f"Retrieving public key for user: {did}")
        
        result = await KeyService.get_user_public_key(did)
        
        return result
        
    except ValueError as e:
        logger.warning(f"Public key not found for user: {did}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_user_public_key endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{did}/signature")
async def generate_signature(did: str):
    """Generate HMAC signature for WebSocket authentication"""
    try:
        logger.info(f"Generating signature for user: {did}")
        
        # Check if user exists and has a public key
        try:
            existing_key = await KeyService.get_user_public_key(did)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Public key not found for user: {did}"
            )
        
        # Generate timestamp and signature
        from app.core.auth import auth_manager
        timestamp = datetime.utcnow().isoformat()
        signature = auth_manager.create_did_signature(did, timestamp, settings.SECRET_KEY)
        
        return {
            "signature": signature,
            "timestamp": timestamp,
            "did": did,
            "expires_in": 300  # 5 minutes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating signature for {did}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{did}/token")
async def get_access_token(did: str):
    """Get access token for a user"""
    try:
        logger.info(f"Generating access token for user: {did}")
        
        # Check if user exists and has a public key
        try:
            existing_key = await KeyService.get_user_public_key(did)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Public key not found for user: {did}"
            )
        
        # Generate JWT token
        from app.core.auth import auth_manager
        token_data = {"did": did, "type": "websocket_access"}
        access_token = auth_manager.create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "did": did
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating access token for {did}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Убираем опасный endpoint для принудительной ротации ключей
# Ротация происходит только автоматически каждые 24 часа
# Это предотвращает атаки злоумышленников на принудительную смену ключей


@router.get("/key-rotation/info")
async def get_key_rotation_info():
    """Get information about secret key rotation (read-only)"""
    try:
        logger.debug("Key rotation info requested")
        
        from app.core.auth import auth_manager
        rotation_info = auth_manager.get_key_rotation_info()
        
        # Убираем чувствительную информацию
        safe_rotation_info = {
            "last_rotation": rotation_info["last_rotation"],
            "next_rotation": rotation_info["next_rotation"],
            "rotation_interval_hours": rotation_info["rotation_interval_hours"],
            "previous_keys_count": rotation_info["previous_keys_count"],
            "total_keys_managed": rotation_info["total_keys_managed"]
        }
        
        return {
            "status": "success",
            "key_rotation": safe_rotation_info,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Secret key rotation is automatic and secure"
        }
        
    except Exception as e:
        logger.error(f"Error getting key rotation info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{did}/token-info")
async def get_token_info(did: str, token: str):
    """Get information about a JWT token"""
    try:
        logger.info(f"Getting token info for user: {did}")
        
        # Check if user exists and has a public key
        try:
            existing_key = await KeyService.get_user_public_key(did)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Public key not found for user: {did}"
            )
        
        # Decode token to get information
        from app.core.auth import auth_manager
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
            
            # Check if token is revoked or blacklisted
            is_revoked = token in auth_manager.revoked_tokens
            is_blacklisted = token in auth_manager.token_blacklist
            
            # Calculate time until expiration
            exp_timestamp = payload.get("exp", 0)
            current_time = datetime.utcnow()
            exp_time = datetime.fromtimestamp(exp_timestamp)
            time_until_exp = (exp_time - current_time).total_seconds()
            
            token_info = {
                "did": payload.get("did"),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)).isoformat() if payload.get("iat") else None,
                "expires_at": exp_time.isoformat() if exp_timestamp else None,
                "time_until_exp": max(0, int(time_until_exp)),
                "is_expired": time_until_exp <= 0,
                "is_revoked": is_revoked,
                "is_blacklisted": is_blacklisted,
                "token_type": payload.get("type"),
                "jti": payload.get("jti")
            }
            
            return token_info
            
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=400,
                detail="Invalid token format"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token info for {did}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{did}/blacklist-token")
async def blacklist_user_token(did: str, token: str):
    """Permanently blacklist a JWT token for a user"""
    try:
        logger.info(f"Blacklisting token for user: {did}")
        
        # Check if user exists and has a public key
        try:
            existing_key = await KeyService.get_user_public_key(did)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Public key not found for user: {did}"
            )
        
        # Add token to blacklist
        from app.core.auth import auth_manager
        success = auth_manager.blacklist_token(token)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to blacklist token"
            )
        
        return {
            "status": "success",
            "message": "Token blacklisted successfully",
            "did": did,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blacklisting token for {did}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{did}/revoke-token")
async def revoke_user_token(did: str, token: str):
    """Revoke a specific JWT token for a user"""
    try:
        logger.info(f"Revoking token for user: {did}")
        
        # Check if user exists and has a public key
        try:
            existing_key = await KeyService.get_user_public_key(did)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Public key not found for user: {did}"
            )
        
        # Revoke the token
        from app.core.auth import auth_manager
        success = auth_manager.revoke_token(token)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to revoke token"
            )
        
        return {
            "status": "success",
            "message": "Token revoked successfully",
            "did": did,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking token for {did}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/{did}")
async def revoke_public_key(did: str):
    """Revoke public key for a user"""
    try:
        logger.info(f"Revoking public key for user: {did}")
        
        # Check if user exists and has a public key
        try:
            existing_key = await KeyService.get_user_public_key(did)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Public key not found for user: {did}"
            )
        
        # Revoke the key by deleting it from database
        from app.database.Message_database import delete_public_key
        await delete_public_key(did)
        
        # Notify other users about key revocation (if they're connected)
        from app.websocket.manager import manager
        revocation_notification = {
            "type": "key_revoked",
            "data": {
                "did": did,
                "message": "Public key has been revoked",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Broadcast to all connected users except the revoked user
        await manager.broadcast_message(revocation_notification, exclude_did=did)
        
        return {
            "status": "success",
            "message": "Public key revoked successfully",
            "did": did,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in revoke_public_key endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
