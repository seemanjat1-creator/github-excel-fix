from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.models.user import User
from app.auth.auth_handler import get_current_active_user
from app.services.message_queue import message_queue
from app.services.scheduler_service import scheduler_service
from app.services.export_scheduler import export_scheduler
from app.database import get_database
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/system/health")
async def get_system_health(
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive system health status"""
    try:
        # Message queue stats
        queue_stats = await message_queue.get_queue_stats()
        
        # Scheduler status
        scheduler_status = scheduler_service.get_job_status()
        
        # Export scheduler status
        export_status = export_scheduler.get_scheduler_status()
        
        # Database health
        db = get_database()
        db_health = await _check_database_health(db)
        
        # Overall system status
        system_status = "healthy"
        issues = []
        
        # Check for issues
        if queue_stats.get('queue_length', 0) > 50:
            issues.append("Message queue backing up")
            system_status = "warning"
        
        if queue_stats.get('success_rate', 100) < 90:
            issues.append("Low message processing success rate")
            system_status = "warning"
        
        if not db_health.get('connected'):
            issues.append("Database connection issues")
            system_status = "error"
        
        if scheduler_status.get('status') != 'running':
            issues.append("Scheduler not running")
            system_status = "error"
        
        if export_status.get('status') != 'running':
            issues.append("Export scheduler not running")
            system_status = "error"
        
        return {
            "system_status": system_status,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": issues,
            "components": {
                "message_queue": queue_stats,
                "scheduler": scheduler_status,
                "export_scheduler": export_status,
                "database": db_health
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )

@router.get("/queue/stats")
async def get_queue_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed message queue statistics"""
    try:
        stats = await message_queue.get_queue_stats()
        
        # Get additional metrics
        db = get_database()
        
        # Messages by hour for last 24 hours
        hourly_stats = await _get_hourly_message_stats(db)
        
        # Failed messages details
        failed_messages = await db.message_queue.find({
            "status": "failed",
            "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
        }).limit(10).to_list(None)
        
        return {
            "current_stats": stats,
            "hourly_breakdown": hourly_stats,
            "recent_failures": [
                {
                    "message_id": msg["message_id"],
                    "error": msg.get("error_log", [])[-1] if msg.get("error_log") else None,
                    "created_at": msg["created_at"].isoformat(),
                    "retry_count": msg.get("retry_count", 0)
                }
                for msg in failed_messages
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue statistics"
        )

@router.get("/performance/metrics")
async def get_performance_metrics(
    hours: int = 24,
    current_user: User = Depends(get_current_active_user)
):
    """Get system performance metrics"""
    try:
        db = get_database()
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Message processing metrics
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": cutoff_time}
                }
            },
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "avg_processing_time": {"$avg": "$processing_time"}
                }
            }
        ]
        
        processing_metrics = {}
        async for result in db.message_queue.aggregate(pipeline):
            processing_metrics[result["_id"]] = {
                "count": result["count"],
                "avg_processing_time": round(result.get("avg_processing_time", 0), 2)
            }
        
        # Chat activity metrics
        chat_metrics = await _get_chat_activity_metrics(db, cutoff_time)
        
        # AI response metrics
        ai_metrics = await _get_ai_response_metrics(db, cutoff_time)
        
        return {
            "time_period": f"Last {hours} hours",
            "message_processing": processing_metrics,
            "chat_activity": chat_metrics,
            "ai_responses": ai_metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance metrics"
        )

@router.post("/queue/retry-failed")
async def retry_failed_messages(
    current_user: User = Depends(get_current_active_user)
):
    """Retry all failed messages in the queue"""
    try:
        # Only allow admins to retry failed messages
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can retry failed messages"
            )
        
        db = get_database()
        
        # Get failed messages
        failed_messages = await db.message_queue.find({
            "status": "failed",
            "retry_count": {"$lt": 3}
        }).to_list(None)
        
        if not failed_messages:
            return {
                "success": True,
                "message": "No failed messages to retry",
                "retried_count": 0
            }
        
        # Reset failed messages for retry
        message_ids = [msg["message_id"] for msg in failed_messages]
        
        await db.message_queue.update_many(
            {"message_id": {"$in": message_ids}},
            {"$set": {
                "status": "pending",
                "retry_count": 0,
                "error_log": [],
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Re-enqueue messages
        import json
        for msg in failed_messages:
            queue_data = {
                "message_id": msg["message_id"],
                "data": {
                    "phone_number": msg.get("phone_number"),
                    "from": msg.get("from_phone"),
                    "message": msg.get("content"),
                    "type": msg.get("message_type", "text")
                },
                "enqueued_at": datetime.utcnow().isoformat(),
                "priority": "retry"
            }
            
            await message_queue.redis_client.lpush("whatsapp_messages", json.dumps(queue_data))
        
        return {
            "success": True,
            "message": f"Retried {len(failed_messages)} failed messages",
            "retried_count": len(failed_messages)
        }
        
    except Exception as e:
        logger.error(f"Failed to retry messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry failed messages"
        )

async def _check_database_health(db) -> Dict[str, Any]:
    """Check database connection and performance"""
    try:
        # Test connection
        await db.command("ping")
        
        # Get collection stats
        collections = ["users", "workspaces", "chats", "messages", "documents"]
        collection_stats = {}
        
        for collection_name in collections:
            try:
                count = await db[collection_name].count_documents({})
                collection_stats[collection_name] = count
            except Exception as e:
                collection_stats[collection_name] = f"Error: {e}"
        
        return {
            "connected": True,
            "collections": collection_stats,
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }

async def _get_hourly_message_stats(db) -> List[Dict[str, Any]]:
    """Get message statistics by hour for last 24 hours"""
    try:
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
                }
            },
            {
                "$group": {
                    "_id": {
                        "hour": {"$hour": "$created_at"},
                        "status": "$status"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.hour": 1}
            }
        ]
        
        hourly_data = {}
        async for result in db.message_queue.aggregate(pipeline):
            hour = result["_id"]["hour"]
            status = result["_id"]["status"]
            count = result["count"]
            
            if hour not in hourly_data:
                hourly_data[hour] = {}
            
            hourly_data[hour][status] = count
        
        return [
            {
                "hour": hour,
                "stats": stats
            }
            for hour, stats in sorted(hourly_data.items())
        ]
        
    except Exception as e:
        logger.error(f"Failed to get hourly stats: {e}")
        return []

async def _get_chat_activity_metrics(db, cutoff_time: datetime) -> Dict[str, Any]:
    """Get chat activity metrics"""
    try:
        # Active chats
        active_chats = await db.chats.count_documents({
            "status": "active",
            "last_message_at": {"$gte": cutoff_time}
        })
        
        # New chats
        new_chats = await db.chats.count_documents({
            "created_at": {"$gte": cutoff_time}
        })
        
        # Qualified leads
        qualified_leads = await db.chats.count_documents({
            "status": "qualified",
            "updated_at": {"$gte": cutoff_time}
        })
        
        return {
            "active_chats": active_chats,
            "new_chats": new_chats,
            "qualified_leads": qualified_leads
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat metrics: {e}")
        return {}

async def _get_ai_response_metrics(db, cutoff_time: datetime) -> Dict[str, Any]:
    """Get AI response performance metrics"""
    try:
        # AI generated messages
        ai_messages = await db.messages.count_documents({
            "is_ai_generated": True,
            "timestamp": {"$gte": cutoff_time}
        })
        
        # Total outgoing messages
        total_outgoing = await db.messages.count_documents({
            "direction": "outgoing",
            "timestamp": {"$gte": cutoff_time}
        })
        
        # Calculate AI usage percentage
        ai_percentage = (ai_messages / total_outgoing * 100) if total_outgoing > 0 else 0
        
        return {
            "ai_generated_messages": ai_messages,
            "total_outgoing_messages": total_outgoing,
            "ai_usage_percentage": round(ai_percentage, 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to get AI metrics: {e}")
        return {}