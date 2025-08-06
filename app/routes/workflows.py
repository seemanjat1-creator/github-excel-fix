from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.user import User
from app.models.workflow import (
    WorkflowStep, WorkflowStepCreate, WorkflowStepUpdate, 
    ChatWorkflowProgress, WorkflowAnalysis
)
from app.auth.auth_handler import get_current_active_user, verify_workspace_access
from app.services.workflow_service import workflow_service
from app.database import get_database
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/workspace/{workspace_id}", response_model=List[WorkflowStep])
async def get_workspace_workflow_steps(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all workflow steps for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    return await workflow_service.get_workspace_workflow_steps(workspace_id)

@router.post("/", response_model=WorkflowStep)
async def create_workflow_step(
    step: WorkflowStepCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create new workflow step (admin only)"""
    if not await verify_workspace_access(current_user, step.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Check if user is admin
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(step.workspace_id)})
    if str(workspace["admin_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace admin can create workflow steps"
        )
    
    return await workflow_service.create_workflow_step(step)

@router.put("/{step_id}", response_model=WorkflowStep)
async def update_workflow_step(
    step_id: str,
    step_update: WorkflowStepUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update workflow step (admin only)"""
    step = await workflow_service.get_workflow_step_by_id(step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow step not found"
        )
    
    if not await verify_workspace_access(current_user, step.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Check if user is admin
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(step.workspace_id)})
    if str(workspace["admin_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace admin can update workflow steps"
        )
    
    return await workflow_service.update_workflow_step(step_id, step_update)

@router.delete("/{step_id}")
async def delete_workflow_step(
    step_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete workflow step (admin only)"""
    step = await workflow_service.get_workflow_step_by_id(step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow step not found"
        )
    
    if not await verify_workspace_access(current_user, step.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Check if user is admin
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(step.workspace_id)})
    if str(workspace["admin_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace admin can delete workflow steps"
        )
    
    success = await workflow_service.delete_workflow_step(step_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow step not found"
        )
    
    return {"message": "Workflow step deleted successfully"}

@router.get("/progress/{chat_id}")
async def get_chat_workflow_progress(
    chat_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get workflow progress for a chat"""
    # Verify chat access through chat service
    from app.services.chat_service import chat_service
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
    
    return await workflow_service.get_chat_workflow_progress(chat_id)

@router.post("/reorder")
async def reorder_workflow_steps(
    workspace_id: str,
    step_orders: List[dict],  # [{"step_id": "...", "step_number": 1}, ...]
    current_user: User = Depends(get_current_active_user)
):
    """Reorder workflow steps (admin only)"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Check if user is admin
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if str(workspace["admin_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace admin can reorder workflow steps"
        )
    
    success = await workflow_service.reorder_workflow_steps(workspace_id, step_orders)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reorder workflow steps"
        )
    
    return {"message": "Workflow steps reordered successfully"}