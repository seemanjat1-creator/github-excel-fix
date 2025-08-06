from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from app.services.message_queue import message_queue
from app.models.phone_number import PhoneStatus
import logging
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

router = APIRouter()

@asynccontextmanager
async def webhook_timeout(timeout_seconds: int = 300):  # 5 minutes default
    """Context manager to handle webhook timeouts"""
    try:
        # Create a task that will be cancelled after timeout
        task = asyncio.current_task()
        if task:
            # Schedule cancellation after timeout
            asyncio.create_task(asyncio.sleep(timeout_seconds)).add_done_callback(
                lambda _: task.cancel() if not task.done() else None
            )
        yield
    except asyncio.CancelledError:
        logger.warning("Webhook processing timed out after 5 minutes")
        raise HTTPException(status_code=408, detail="Webhook processing timeout")
    except Exception as e:
        logger.error(f"Webhook timeout error: {e}")
        raise

@router.post("/whatsapp/message")
async def whatsapp_message_webhook(request: Request):
    """
    Webhook endpoint for receiving WhatsApp messages from Node.js server
    
    Expected payload:
    {
        "phone_number": "918949470290",
        "from": "918949470291",
        "message": "Hello",
        "type": "text",
        "timestamp": "2025-01-15T10:30:00Z"
    }
    """
    async with webhook_timeout(300):  # 5 minutes timeout
        try:
            webhook_data = await request.json()
            logger.info(f"Received WhatsApp webhook: {webhook_data}")
            
            # Validate required fields
            required_fields = ["phone_number", "from", "message"]
            for field in required_fields:
                if not webhook_data.get(field):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Missing required field: {field}"
                    )
            
            # Enqueue message for processing
            message_id = await message_queue.enqueue_message(webhook_data)
            
            return {
                "status": "success", 
                "message": "Message queued for processing",
                "message_id": message_id
            }
            
        except asyncio.CancelledError:
            logger.warning("WhatsApp message webhook timed out")
            raise HTTPException(status_code=408, detail="Webhook processing timeout")
        except Exception as e:
            logger.error(f"WhatsApp webhook error: {e}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/whatsapp/status")
async def whatsapp_status_webhook(request: Request):
    """
    Webhook endpoint for receiving WhatsApp connection status updates
    
    Expected payload:
    {
        "phone_number": "918949470290",
        "status": "connected",
        "qr_code": "base64_qr_code_data" (optional)
    }
    """
    async with webhook_timeout(300):  # 5 minutes timeout
        try:
            webhook_data = await request.json()
            logger.info(f"Received WhatsApp status webhook: {webhook_data}")
            
            phone_number = webhook_data.get("phone_number")
            status = webhook_data.get("status")
            qr_code = webhook_data.get("qr_code")
            
            if not phone_number or not status:
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Map status to enum
            status_mapping = {
                "connected": PhoneStatus.CONNECTED,
                "disconnected": PhoneStatus.DISCONNECTED,
                "connecting": PhoneStatus.CONNECTING,
                "error": PhoneStatus.ERROR
            }
            
            phone_status = status_mapping.get(status, PhoneStatus.ERROR)
            
            # Update phone status in database
            from app.services.whatsapp_service import whatsapp_service
            await whatsapp_service.update_phone_status(phone_number, phone_status, qr_code)
            
            return {"status": "success", "message": "Status updated"}
            
        except asyncio.CancelledError:
            logger.warning("WhatsApp status webhook timed out")
            raise HTTPException(status_code=408, detail="Webhook processing timeout")
        except Exception as e:
            logger.error(f"WhatsApp status webhook error: {e}")
            raise HTTPException(status_code=500, detail="Status webhook processing failed")

@router.post("/whatsapp/qr")
async def whatsapp_qr_webhook(request: Request):
    """
    Webhook endpoint for receiving QR code URLs from Node.js server
    
    Expected payload:
    {
        "phone": "919999999999",
        "qr_url": "http://localhost:3000/qr/919999999999.png"
    }
    """
    async with webhook_timeout(300):  # 5 minutes timeout
        try:
            webhook_data = await request.json()
            logger.info(f"Received WhatsApp QR webhook: {webhook_data}")
            
            phone_number = webhook_data.get("phone")
            qr_url = webhook_data.get("qr_url")
            
            if not phone_number or not qr_url:
                raise HTTPException(status_code=400, detail="Missing phone or qr_url")
            
            # Update phone status to WAITING_FOR_SCAN and store QR URL
            from app.services.whatsapp_service import whatsapp_service
            await whatsapp_service.update_phone_status(
                phone_number, 
                PhoneStatus.CONNECTING, 
                qr_url
            )
            
            return {"status": "success", "message": "QR URL received and stored"}
            
        except asyncio.CancelledError:
            logger.warning("WhatsApp QR webhook timed out")
            raise HTTPException(status_code=408, detail="Webhook processing timeout")
        except Exception as e:
            logger.error(f"WhatsApp QR webhook error: {e}")
            raise HTTPException(status_code=500, detail="QR webhook processing failed")

@router.post("/whatsapp/delivery")
async def whatsapp_delivery_webhook(request: Request):
    """
    Webhook endpoint for receiving WhatsApp message delivery status
    
    Expected payload:
    {
        "phone_number": "918949470290",
        "to": "918949470291",
        "message_id": "msg_123",
        "status": "delivered",
        "timestamp": "2025-01-15T10:30:00Z"
    }
    """
    async with webhook_timeout(300):  # 5 minutes timeout
        try:
            webhook_data = await request.json()
            logger.info(f"Received WhatsApp delivery webhook: {webhook_data}")
            
            # Update message delivery status in database
            message_id = webhook_data.get("message_id")
            status = webhook_data.get("status")
            
            if message_id and status:
                db = get_database()
                await db.messages.update_one(
                    {"external_message_id": message_id},
                    {"$set": {
                        "delivery_status": status,
                        "delivered_at": datetime.utcnow()
                    }}
                )
            
            return {"status": "success", "message": "Delivery status updated"}
            
        except asyncio.CancelledError:
            logger.warning("WhatsApp delivery webhook timed out")
            raise HTTPException(status_code=408, detail="Webhook processing timeout")
        except Exception as e:
            logger.error(f"WhatsApp delivery webhook error: {e}")
            raise HTTPException(status_code=500, detail="Delivery webhook processing failed")

@router.get("/whatsapp/health")
async def whatsapp_health_check():
    """Health check endpoint for WhatsApp integration"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "whatsapp-webhook"
    }