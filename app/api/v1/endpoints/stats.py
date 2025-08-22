"""
Statistics API endpoints
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.database.database import async_session, PublicKey, PrivateMessage
from app.websocket.manager import manager
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/overview")
async def get_system_overview():
    """Get system overview statistics"""
    try:
        logger.debug("System overview requested")
        
        # Get database statistics
        async with async_session() as session:
            # Total users
            total_users_result = await session.execute(
                select(func.count(PublicKey.did))
            )
            total_users = total_users_result.scalar() or 0
            
            # Total messages
            total_messages_result = await session.execute(
                select(func.count(PrivateMessage.id))
            )
            total_messages = total_messages_result.scalar() or 0
            
            # Messages in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_messages_result = await session.execute(
                select(func.count(PrivateMessage.id)).where(
                    PrivateMessage.timestamp >= yesterday
                )
            )
            recent_messages = recent_messages_result.scalar() or 0
        
        # Get WebSocket statistics
        connected_users = await manager.get_connected_users()
        connection_count = await manager.get_connection_count()
        
        # Calculate message rate
        message_rate = recent_messages / 24 if recent_messages > 0 else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "users": {
                "total": total_users,
                "connected": connection_count,
                "online_percentage": round((connection_count / total_users * 100) if total_users > 0 else 0, 2)
            },
            "messages": {
                "total": total_messages,
                "last_24h": recent_messages,
                "rate_per_hour": round(message_rate, 2)
            },
            "system": {
                "status": "healthy",
                "uptime": "running"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/users/activity")
async def get_user_activity():
    """Get user activity statistics"""
    try:
        logger.debug("User activity requested")
        
        async with async_session() as session:
            # Get most active users (by message count)
            active_users_result = await session.execute(
                select(
                    PrivateMessage.sender_did,
                    func.count(PrivateMessage.id).label('message_count')
                ).group_by(PrivateMessage.sender_did)
                .order_by(func.count(PrivateMessage.id).desc())
                .limit(10)
            )
            
            active_users = [
                {
                    "did": row.sender_did,
                    "message_count": row.message_count
                }
                for row in active_users_result
            ]
            
            # Get recent registrations (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_registrations_result = await session.execute(
                select(func.count(PublicKey.did)).where(
                    PublicKey.created_at >= week_ago
                )
            )
            recent_registrations = recent_registrations_result.scalar() or 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_users": active_users,
            "recent_registrations": recent_registrations,
            "top_sender": active_users[0] if active_users else None
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/messages/trends")
async def get_message_trends():
    """Get message trends over time"""
    try:
        logger.debug("Message trends requested")
        
        async with async_session() as session:
            # Get message count by hour for last 24 hours
            trends = []
            for i in range(24):
                hour_start = datetime.utcnow() - timedelta(hours=i+1)
                hour_end = datetime.utcnow() - timedelta(hours=i)
                
                count_result = await session.execute(
                    select(func.count(PrivateMessage.id)).where(
                        PrivateMessage.timestamp >= hour_start,
                        PrivateMessage.timestamp < hour_end
                    )
                )
                count = count_result.scalar() or 0
                
                trends.append({
                    "hour": hour_start.strftime("%H:00"),
                    "message_count": count
                })
            
            # Reverse to show chronological order
            trends.reverse()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": "last_24_hours",
            "trends": trends,
            "total_messages": sum(t["message_count"] for t in trends),
            "peak_hour": max(trends, key=lambda x: x["message_count"]) if trends else None
        }
        
    except Exception as e:
        logger.error(f"Error getting message trends: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
