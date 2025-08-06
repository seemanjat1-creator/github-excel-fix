from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.user import User
from app.models.chat import Chat, ChatCreate, ChatUpdate, Message, MessageCreate, ChatSummary
from app.auth.auth_handler import get_current_active_user, verify_workspace_access
from app.services.chat_service import chat_service
from app.database import get_database
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/workspace/{workspace_id}", response_model=List[Chat])
async def get_workspace_chats(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all chats for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    return await chat_service.get_workspace_chats(workspace_id)

@router.get("/{chat_id}", response_model=Chat)
async def get_chat(
    chat_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get chat by ID"""
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Verify workspace access
    if not await verify_workspace_access(current_user, chat.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to chat"
        )
    
    return chat

@router.post("/", response_model=Chat)
async def create_chat(
    chat: ChatCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create new chat"""
    if not await verify_workspace_access(current_user, chat.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    return await chat_service.create_chat(chat)

@router.put("/{chat_id}", response_model=Chat)
async def update_chat(
    chat_id: str,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update chat"""
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if not await verify_workspace_access(current_user, chat.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to chat"
        )
    
    updated_chat = await chat_service.update_chat(chat_id, chat_update)
    if not updated_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return updated_chat

@router.post("/{chat_id}/messages", response_model=Message)
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Send message to chat"""
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if not await verify_workspace_access(current_user, chat.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to chat"
        )
    
    return await chat_service.add_message(chat_id, message_data)

@router.put("/{chat_id}/status")
async def update_chat_status(
    chat_id: str,
    status: str,
    current_user: User = Depends(get_current_active_user)
):
    """Update chat status"""
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if not await verify_workspace_access(current_user, chat.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to chat"
        )
    
    chat_update = ChatUpdate(status=status)
    return await chat_service.update_chat(chat_id, chat_update)

@router.get("/qualified-leads/{workspace_id}", response_model=List[ChatSummary])
async def get_qualified_leads(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get qualified leads for workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    return await chat_service.get_qualified_leads(workspace_id)

@router.post("/{chat_id}/summary")
async def generate_chat_summary(
    chat_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Generate summary for chat"""
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if not await verify_workspace_access(current_user, chat.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to chat"
        )
    
    summary = await chat_service.generate_chat_summary(chat_id)
    return {"summary": summary}