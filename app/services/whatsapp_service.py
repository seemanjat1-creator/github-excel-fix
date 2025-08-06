import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.models.chat import Chat, Message, MessageCreate, MessageDirection
from app.models.phone_number import PhoneNumber, PhoneStatus
from app.database import get_database
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.whatsapp_server_url = settings.whatsapp_server_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_message(
        self,
        phone_number: str,
        to_phone: str,
        message: str,
        message_type: str = "text"
    ) -> bool:
        """Send message through WhatsApp Node.js server"""
        try:
            payload = {
                "phone_number": phone_number,
                "to": to_phone,
                "message": message,
                "type": message_type
            }
            
            response = await self.client.post(
                f"{self.whatsapp_server_url}/send-message",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {to_phone}")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"WhatsApp send message error: {e}")
            return False
    
    async def request_qr_code(self, phone_number: str) -> Optional[str]:
        """Request QR code for WhatsApp connection"""
        try:
            clean_number = phone_number.replace("+", "")
            payload = {
                "phone_number": clean_number,
                # "webhook_url": f"{settings.whatsapp_server_url}/webhook/qr/{phone_number}"
            }
            
            response = await self.client.post(
                f"{self.whatsapp_server_url}/phones/{clean_number}/connect",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("qrUrl")
            else:
                logger.error(f"Failed to request QR code: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"WhatsApp QR code request error: {e}")
            return None
    
    async def disconnect_phone(self, phone_number: str) -> bool:
        """Disconnect WhatsApp phone number"""
        try:
            response = await self.client.post(
            f"{self.whatsapp_server_url}/phones/{phone_number}/disconnect"
            )

            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"WhatsApp disconnect error: {e}")
            return False
    
    async def get_connection_status(self, phone_number: str) -> PhoneStatus:
        """Get connection status of WhatsApp phone number"""
        try:
            response = await self.client.get(
                f"{self.whatsapp_server_url}/status/{phone_number}"
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "disconnected")
                
                # Map status to enum
                if status == "connected":
                    return PhoneStatus.CONNECTED
                elif status == "connecting":
                    return PhoneStatus.CONNECTING
                elif status == "error":
                    return PhoneStatus.ERROR
                else:
                    return PhoneStatus.DISCONNECTED
            else:
                return PhoneStatus.ERROR
                
        except Exception as e:
            logger.error(f"WhatsApp status check error: {e}")
            return PhoneStatus.ERROR
    
    async def process_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Message]:
        """Process incoming WhatsApp message from webhook"""
        try:
            phone_number = webhook_data.get("phone_number")
            from_phone = webhook_data.get("from")
            message_content = webhook_data.get("message")
            message_type = webhook_data.get("type", "text")
            
            if not all([phone_number, from_phone, message_content]):
                logger.error("Missing required fields in webhook data")
                return None
            
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
                    logger.error(f"Phone number {phone_number} not found")
                    return None
                
                chat_data = {
                    "workspace_id": phone_doc["workspace_id"],
                    "phone_number": phone_number,
                    "customer_phone": from_phone,
                    "status": "active",
                    "ai_enabled": True,
                    "workflow_progress": {},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                result = await db.chats.insert_one(chat_data)
                chat_data["_id"] = result.inserted_id
            
            # Create message
            message_data = {
                "chat_id": str(chat_data["_id"]),
                "content": message_content,
                "message_type": message_type,
                "direction": MessageDirection.INCOMING,
                "timestamp": datetime.utcnow(),
                "is_ai_generated": False
            }
            
            result = await db.messages.insert_one(message_data)
            message_data["_id"] = str(result.inserted_id)
            
            # Update chat last message time
            await db.chats.update_one(
                {"_id": chat_data["_id"]},
                {"$set": {"last_message_at": datetime.utcnow()}}
            )
            
            return Message(**message_data)
            
        except Exception as e:
            logger.error(f"Process incoming message error: {e}")
            return None
    
    async def update_phone_status(self, phone_number: str, status: PhoneStatus, qr_code: Optional[str] = None):
        """Update phone number status in database"""
        try:
            db = get_database()
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            if qr_code:
                update_data["qr_code"] = qr_code
            
            if status == PhoneStatus.CONNECTED:
                update_data["last_connected_at"] = datetime.utcnow()
                update_data["qr_code"] = None  # Clear QR code when connected
            
            await db.phone_numbers.update_one(
                {"phone_number": phone_number},
                {"$set": update_data}
            )
            
        except Exception as e:
            logger.error(f"Update phone status error: {e}")

whatsapp_service = WhatsAppService()