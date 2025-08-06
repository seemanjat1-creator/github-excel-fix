import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import redis.asyncio as redis
from app.config import settings
from app.database import get_database
from app.models.chat import MessageCreate, MessageDirection
from app.services.chat_service import chat_service
from app.services.whatsapp_service import whatsapp_service
from bson import ObjectId
import traceback

logger = logging.getLogger(__name__)

class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class MessageQueue:
    def __init__(self):
        self.redis_client = None
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.processing_timeout = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def enqueue_message(self, message_data: Dict[str, Any]) -> str:
        """
        Enqueue incoming WhatsApp message for processing
        Returns message ID for tracking
        """
        try:
            # Generate unique message ID
            message_id = f"msg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{message_data.get('from', 'unknown')}"
            
            # Create message record in database
            db = get_database()
            message_record = {
                "message_id": message_id,
                "phone_number": message_data.get("phone_number"),
                "from_phone": message_data.get("from"),
                "content": message_data.get("message"),
                "message_type": message_data.get("type", "text"),
                "status": MessageStatus.PENDING,
                "created_at": datetime.utcnow(),
                "retry_count": 0,
                "error_log": [],
                "processing_time": None,
                "completed_at": None
            }
            
            await db.message_queue.insert_one(message_record)
            
            # Add to Redis queue
            queue_data = {
                "message_id": message_id,
                "data": message_data,
                "enqueued_at": datetime.utcnow().isoformat(),
                "priority": "normal"
            }
            
            await self.redis_client.lpush("whatsapp_messages", json.dumps(queue_data))
            
            logger.info(f"Message {message_id} enqueued successfully")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            raise
    
    async def process_messages(self):
        """
        Main message processing loop
        Should be run as a background task
        """
        logger.info("Starting message processing loop")
        
        while True:
            try:
                # Get message from queue (blocking with timeout)
                result = await self.redis_client.brpop("whatsapp_messages", timeout=10)
                
                if result:
                    queue_name, message_data = result
                    await self._process_single_message(json.loads(message_data))
                
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_single_message(self, queue_data: Dict[str, Any]):
        """Process a single message from the queue"""
        message_id = queue_data.get("message_id")
        message_data = queue_data.get("data")
        
        try:
            logger.info(f"Processing message {message_id}")
            start_time = datetime.utcnow()
            
            # Update status to processing
            await self._update_message_status(message_id, MessageStatus.PROCESSING)
            
            # Process the message
            await self._handle_incoming_message(message_data)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update status to completed
            await self._update_message_status(
                message_id, 
                MessageStatus.COMPLETED,
                processing_time=processing_time
            )
            
            logger.info(f"Message {message_id} processed successfully in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            await self._handle_message_failure(message_id, str(e), queue_data)
    
    async def _handle_incoming_message(self, message_data: Dict[str, Any]):
        """Handle the actual message processing logic"""
        phone_number = message_data.get("phone_number")
        from_phone = message_data.get("from")
        message_content = message_data.get("message")
        message_type = message_data.get("type", "text")
        
        if not all([phone_number, from_phone, message_content]):
            raise ValueError("Missing required message fields")
        
        # Find or create chat
        db = get_database()
        chat_data = await db.chats.find_one({
            "phone_number": phone_number,
            "customer_phone": from_phone
        })
        
        if not chat_data:
            # Create new chat
            phone_doc = await db.phone_numbers.find_one({"phone_number": phone_number})
            if not phone_doc:
                raise ValueError(f"Phone number {phone_number} not found")
            
            from app.models.chat import ChatCreate
            chat_create = ChatCreate(
                workspace_id=str(phone_doc["workspace_id"]),
                phone_number=phone_number,
                customer_phone=from_phone,
                ai_enabled=True
            )
            
            chat = await chat_service.create_chat(chat_create)
            chat_id = chat.id
        else:
            chat_id = str(chat_data["_id"])
        
        # Create incoming message
        message_create = MessageCreate(
            content=message_content,
            message_type=message_type,
            direction=MessageDirection.INCOMING
        )
        
        # Save message
        message = await chat_service.add_message(chat_id, message_create)
        
        # Generate AI response if enabled
        try:
            ai_response = await chat_service.process_ai_response(chat_id, message_content)
            if ai_response:
                logger.info(f"AI response generated for chat {chat_id}")
        except Exception as e:
            logger.error(f"AI response generation failed for chat {chat_id}: {e}")
            # Don't fail the entire message processing if AI fails
            # Send fallback message
            fallback_message = "Thank you for your message. We'll get back to you shortly."
            
            fallback_message_create = MessageCreate(
                content=fallback_message,
                direction=MessageDirection.OUTGOING,
                is_ai_generated=False
            )
            
            await chat_service.add_message(chat_id, fallback_message_create)
            
            # Try to send via WhatsApp
            try:
                await whatsapp_service.send_message(phone_number, from_phone, fallback_message)
            except Exception as send_error:
                logger.error(f"Failed to send fallback message: {send_error}")
    
    async def _handle_message_failure(self, message_id: str, error: str, queue_data: Dict[str, Any]):
        """Handle message processing failure with retry logic"""
        db = get_database()
        
        # Get current message record
        message_record = await db.message_queue.find_one({"message_id": message_id})
        if not message_record:
            logger.error(f"Message record {message_id} not found")
            return
        
        retry_count = message_record.get("retry_count", 0)
        error_log = message_record.get("error_log", [])
        
        # Add error to log
        error_log.append({
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_attempt": retry_count + 1
        })
        
        if retry_count < self.max_retries:
            # Schedule retry
            retry_count += 1
            await db.message_queue.update_one(
                {"message_id": message_id},
                {"$set": {
                    "status": MessageStatus.RETRY,
                    "retry_count": retry_count,
                    "error_log": error_log,
                    "next_retry_at": datetime.utcnow() + timedelta(seconds=self.retry_delay * retry_count)
                }}
            )
            
            # Re-enqueue with delay
            await asyncio.sleep(self.retry_delay * retry_count)
            await self.redis_client.lpush("whatsapp_messages", json.dumps(queue_data))
            
            logger.info(f"Message {message_id} scheduled for retry {retry_count}/{self.max_retries}")
        else:
            # Mark as failed
            await self._update_message_status(
                message_id, 
                MessageStatus.FAILED,
                error_log=error_log
            )
            logger.error(f"Message {message_id} failed permanently after {self.max_retries} retries")
    
    async def _update_message_status(
        self, 
        message_id: str, 
        status: MessageStatus,
        processing_time: Optional[float] = None,
        error_log: Optional[List[Dict]] = None
    ):
        """Update message status in database"""
        db = get_database()
        
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        if processing_time is not None:
            update_data["processing_time"] = processing_time
        
        if status == MessageStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        
        if error_log is not None:
            update_data["error_log"] = error_log
        
        await db.message_queue.update_one(
            {"message_id": message_id},
            {"$set": update_data}
        )
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get message queue statistics"""
        try:
            db = get_database()
            
            # Get queue length from Redis
            queue_length = await self.redis_client.llen("whatsapp_messages")
            
            # Get status counts from database
            pipeline = [
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            status_counts = {}
            async for result in db.message_queue.aggregate(pipeline):
                status_counts[result["_id"]] = result["count"]
            
            # Get processing metrics
            recent_messages = await db.message_queue.find({
                "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}
            }).to_list(None)
            
            avg_processing_time = 0
            if recent_messages:
                processing_times = [
                    msg.get("processing_time", 0) 
                    for msg in recent_messages 
                    if msg.get("processing_time")
                ]
                if processing_times:
                    avg_processing_time = sum(processing_times) / len(processing_times)
            
            return {
                "queue_length": queue_length,
                "status_counts": status_counts,
                "avg_processing_time": round(avg_processing_time, 2),
                "messages_last_hour": len(recent_messages),
                "success_rate": self._calculate_success_rate(recent_messages)
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    def _calculate_success_rate(self, messages: List[Dict]) -> float:
        """Calculate success rate for recent messages"""
        if not messages:
            return 0.0
        
        completed = len([m for m in messages if m.get("status") == MessageStatus.COMPLETED])
        total = len(messages)
        
        return round((completed / total) * 100, 2) if total > 0 else 0.0
    
    async def cleanup_old_messages(self, days: int = 7):
        """Clean up old message queue records"""
        try:
            db = get_database()
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db.message_queue.delete_many({
                "created_at": {"$lt": cutoff_date},
                "status": {"$in": [MessageStatus.COMPLETED, MessageStatus.FAILED]}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old message records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")

# Global message queue instance
message_queue = MessageQueue()