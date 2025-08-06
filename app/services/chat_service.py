from typing import List, Optional, Dict, Any
from app.models.chat import Chat, ChatCreate, ChatUpdate, Message, MessageCreate, ChatSummary, ChatStatus
from app.models.workspace import Workspace, WorkflowStep
from app.services.openai_service import openai_service
from app.services.document_service import document_service
from app.services.whatsapp_service import whatsapp_service
from app.services.workflow_service import workflow_service
from app.database import get_database
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ChatService:
    async def create_chat(self, chat_data: ChatCreate) -> Chat:
        """Create new chat"""
        db = get_database()
        
        chat_dict = chat_data.dict()
        chat_dict["workspace_id"] = ObjectId(chat_data.workspace_id)
        chat_dict["created_at"] = datetime.utcnow()
        chat_dict["updated_at"] = datetime.utcnow()
        
        result = await db.chats.insert_one(chat_dict)
        chat_dict["_id"] = str(result.inserted_id)
        chat_dict["workspace_id"] = chat_data.workspace_id
        
        return Chat(**chat_dict)
    
    async def get_workspace_chats(self, workspace_id: str) -> List[Chat]:
        """Get all chats for a workspace"""
        db = get_database()
        cursor = db.chats.find({"workspace_id": ObjectId(workspace_id)})
        chats = []
        
        async for chat in cursor:
            chat["_id"] = str(chat["_id"])
            chat["workspace_id"] = workspace_id
            
            # Get recent messages
            messages = await self._get_chat_messages(chat["_id"])
            chat["messages"] = messages
            
            chats.append(Chat(**chat))
        
        return chats
    
    async def get_chat_by_id(self, chat_id: str) -> Optional[Chat]:
        """Get chat by ID with messages"""
        db = get_database()
        chat_data = await db.chats.find_one({"_id": ObjectId(chat_id)})
        
        if not chat_data:
            return None
        
        chat_data["_id"] = str(chat_data["_id"])
        chat_data["workspace_id"] = str(chat_data["workspace_id"])
        
        # Get messages
        messages = await self._get_chat_messages(chat_id)
        chat_data["messages"] = messages
        
        return Chat(**chat_data)
    
    async def update_chat(self, chat_id: str, update_data: ChatUpdate) -> Optional[Chat]:
        """Update chat"""
        db = get_database()
        
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await db.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await self.get_chat_by_id(chat_id)
    
    async def add_message(self, chat_id: str, message_data: MessageCreate) -> Message:
        """Add message to chat"""
        if not chat_id or not message_data.content or not message_data.content.strip():
            raise ValueError("Chat ID and message content are required")
        
        db = get_database()
        
        message_dict = message_data.dict()
        message_dict["chat_id"] = chat_id
        message_dict["content"] = message_data.content.strip()
        message_dict["timestamp"] = datetime.utcnow()
        
        result = await db.messages.insert_one(message_dict)
        message_dict["_id"] = str(result.inserted_id)
        
        # Update chat last message time
        await db.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"last_message_at": datetime.utcnow()}}
        )
        
        return Message(**message_dict)
    
    async def process_ai_response(self, chat_id: str, user_message: str) -> Optional[Message]:
        """Process AI response for incoming message"""
        try:
            chat = await self.get_chat_by_id(chat_id)
            if not chat or not chat.ai_enabled:
                return None
            
            # Get workspace and its settings
            db = get_database()
            workspace_data = await db.workspaces.find_one({"_id": ObjectId(chat.workspace_id)})
            if not workspace_data:
                return None
            
            workspace_data["_id"] = str(workspace_data["_id"])
            workspace = Workspace(**workspace_data)
            
            # Get AI settings
            ai_settings = workspace_data.get('ai_settings', {})
            
            # Get workflow steps for this workspace
            workflow_steps = await workflow_service.get_workspace_workflow_steps(chat.workspace_id)
            
            # Get current workflow progress
            workflow_progress = await workflow_service.get_chat_workflow_progress(chat_id)
            current_step = workflow_progress.current_step if workflow_progress else 1
            
            # Analyze message against current workflow step
            if workflow_steps:
                analysis = await workflow_service.analyze_message_against_workflow(
                    message=user_message,
                    workspace_id=chat.workspace_id,
                    current_step=current_step,
                    chat_history=[{"role": "user" if msg.direction == "incoming" else "assistant", "content": msg.content} for msg in chat.messages[-10:]]
                )
                
                # Update workflow progress
                updated_progress = await workflow_service.update_chat_workflow_progress(
                    chat_id=chat_id,
                    workspace_id=chat.workspace_id,
                    analysis=analysis,
                    current_step=current_step
                )
                
                # Check if chat needs human help
                if updated_progress.needs_human_help:
                    await self.update_chat(chat_id, ChatUpdate(
                        status=ChatStatus.UNQUALIFIED,
                        summary="Customer needs human assistance - AI confidence too low"
                    ))
                    
                    ai_response = "I understand you have specific needs. Let me connect you with one of our specialists who can better assist you."
                
                # Check if chat is qualified
                elif updated_progress.is_qualified:
                    await self.update_chat(chat_id, ChatUpdate(
                        status=ChatStatus.QUALIFIED,
                        summary=await openai_service.generate_chat_summary(chat.messages)
                    ))
                    
                    ai_response = "Thank you for providing all the information! You're now qualified for our services. A specialist will contact you shortly."
                
                # Generate workflow-based response
                else:
                    current_step_data = next((step for step in workflow_steps if step.step_number == current_step), None)
                    if current_step_data:
                        # Get relevant documents for context
                        context_docs = await document_service.search_documents(
                            user_message, chat.workspace_id, limit=3
                        )
                        
                        ai_response = await openai_service.generate_workflow_response(
                            current_step=current_step_data,
                            user_message=user_message,
                            chat_history=[{"role": "user" if msg.direction == "incoming" else "assistant", "content": msg.content} for msg in chat.messages[-10:]],
                            workflow_progress=updated_progress.dict(),
                            context_documents=context_docs
                        )
                    else:
                        ai_response = "Thank you for your message. How can I help you today?"
            
            else:
                # Fallback to original logic if no workflow steps
                # Get relevant documents for context
                context_docs = await document_service.search_documents(
                    user_message, chat.workspace_id, limit=3
                )
                
                # Prepare conversation history
                conversation_history = []
                for msg in chat.messages[-10:]:  # Last 10 messages
                    role = "user" if msg.direction == "incoming" else "assistant"
                    conversation_history.append({
                        "role": role,
                        "content": msg.content
                    })
                
                # Add current message
                conversation_history.append({
                    "role": "user",
                    "content": user_message
                })
                
                # Generate AI response
                ai_response = await openai_service.generate_response(
                    conversation_history,
                    ai_settings,
                    context_docs
                )
            # Get relevant documents for context
            context_docs = await document_service.search_documents(
                DocumentSearch(
                    query=user_message,
                    workspace_id=chat.workspace_id,
                    limit=3,
                    similarity_threshold=0.6
                )
            )
            
            # Prepare conversation history
            conversation_history = []
            for msg in chat.messages[-10:]:  # Last 10 messages
                role = "user" if msg.direction == "incoming" else "assistant"
                conversation_history.append({
                    "role": role,
                    "content": msg.content
                })
            
            # Add current message
            conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Extract documents from search results
            context_documents = [result.document for result in context_docs] if context_docs else []
            
            # Generate AI response
            ai_response = await openai_service.generate_response(
                conversation_history,
                workspace.prompt_settings,
                context_documents
            )
            
            # Create AI message
            ai_message = MessageCreate(
                content=ai_response,
                direction="outgoing",
                is_ai_generated=True
            )
            
            # Save AI message
            message = await self.add_message(chat_id, ai_message)
            
            # Send via WhatsApp
            await whatsapp_service.send_message(
                chat.phone_number,
                chat.customer_phone,
                ai_response
            )
            
            return message
            
        except Exception as e:
            logger.error(f"AI response processing error: {e}")
            return None
    
    async def get_qualified_leads(self, workspace_id: str) -> List[ChatSummary]:
        """Get qualified leads with chat summaries"""
        db = get_database()
        cursor = db.chats.find({
            "workspace_id": ObjectId(workspace_id),
            "status": ChatStatus.QUALIFIED
        })
        
        summaries = []
        async for chat in cursor:
            # Get message count
            message_count = await db.messages.count_documents({"chat_id": str(chat["_id"])})
            
            summary = ChatSummary(
                chat_id=str(chat["_id"]),
                customer_phone=chat["customer_phone"],
                customer_name=chat.get("customer_name"),
                summary=chat.get("summary", ""),
                status=chat["status"],
                qualified_at=chat.get("updated_at"),
                total_messages=message_count,
                created_at=chat["created_at"]
            )
            summaries.append(summary)
        
        return summaries
    
    async def get_chats_needing_human_help(self, workspace_id: str) -> List[ChatSummary]:
        """Get chats that need human help"""
        db = get_database()
        
        # Get chats with workflow progress indicating need for human help
        pipeline = [
            {
                "$lookup": {
                    "from": "chat_workflow_progress",
                    "localField": "_id",
                    "foreignField": "chat_id",
                    "as": "workflow_progress"
                }
            },
            {
                "$match": {
                    "workspace_id": ObjectId(workspace_id),
                    "$or": [
                        {"status": ChatStatus.UNQUALIFIED},
                        {"workflow_progress.needs_human_help": True}
                    ]
                }
            }
        ]
        
        summaries = []
        async for chat in db.chats.aggregate(pipeline):
            # Get message count
            message_count = await db.messages.count_documents({"chat_id": str(chat["_id"])})
            
            summary = ChatSummary(
                chat_id=str(chat["_id"]),
                customer_phone=chat["customer_phone"],
                customer_name=chat.get("customer_name"),
                summary=chat.get("summary", "Needs human assistance"),
                status=chat["status"],
                qualified_at=chat.get("updated_at"),
                total_messages=message_count,
                created_at=chat["created_at"]
            )
            summaries.append(summary)
        
        return summaries
    
    async def generate_chat_summary(self, chat_id: str) -> str:
        """Generate summary for a chat"""
        chat = await self.get_chat_by_id(chat_id)
        if not chat:
            return ""
        
        summary = await openai_service.generate_chat_summary(chat.messages)
        
        # Update chat with summary
        await self.update_chat(chat_id, ChatUpdate(summary=summary))
        
        return summary
    
    async def _get_chat_messages(self, chat_id: str) -> List[Message]:
        """Get messages for a chat"""
        db = get_database()
        cursor = db.messages.find({"chat_id": chat_id}).sort("timestamp", 1)
        
        messages = []
        async for msg in cursor:
            msg["_id"] = str(msg["_id"])
            messages.append(Message(**msg))
        
        return messages

chat_service = ChatService()