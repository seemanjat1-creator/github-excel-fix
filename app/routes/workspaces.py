from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate
from app.auth.auth_handler import get_current_active_user, verify_workspace_access, verify_workspace_admin
from app.database import get_database
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Workspace])
async def get_user_workspaces(current_user: User = Depends(get_current_active_user)):
    """Get all workspaces for current user"""
    db = get_database()
    
    # Get workspaces where user is admin or member
    cursor = db.workspaces.find({
        "$or": [
            {"admin_id": ObjectId(current_user.id)},
            {"member_ids": ObjectId(current_user.id)}
        ]
    })
    
    workspaces = []
    async for workspace in cursor:
        workspace["_id"] = str(workspace["_id"])
        workspace["admin_id"] = str(workspace["admin_id"])
        workspace["member_ids"] = [str(member_id) for member_id in workspace.get("member_ids", [])]
        workspaces.append(Workspace(**workspace))
    
    return workspaces

@router.post("/", response_model=Workspace)
async def create_workspace(
    workspace: WorkspaceCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create new workspace (only global admins can create, and are always admin of the workspace).
    Also, make the current user admin of all existing workspaces if they are global admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only global admin users can create workspaces."
        )
    db = get_database()
    # Make current user admin of all existing workspaces
    await db.workspaces.update_many({}, {"$set": {"admin_id": ObjectId(current_user.id)}})
    # Validate input
    if not workspace.name or len(workspace.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Workspace name must be at least 2 characters"
        )
    workspace_dict = workspace.dict()
    workspace_dict["name"] = workspace.name.strip()
    workspace_dict["description"] = workspace.description.strip() if workspace.description else None
    workspace_dict["admin_id"] = ObjectId(current_user.id)  # Always set to current user
    workspace_dict["member_ids"] = []
    workspace_dict["created_at"] = datetime.utcnow()
    workspace_dict["updated_at"] = datetime.utcnow()
    result = await db.workspaces.insert_one(workspace_dict)
    workspace_dict["_id"] = str(result.inserted_id)
    workspace_dict["admin_id"] = current_user.id
    # Add workspace to user's workspace list
    await db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$push": {"workspaces": str(result.inserted_id)}}
    )
    return Workspace(**workspace_dict)

@router.post("/make-admin", response_model=dict)
async def make_current_user_admin_of_all_workspaces(
    current_user: User = Depends(get_current_active_user)
):
    """Make current user admin of all workspaces (for global admins only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only global admin users can perform this action."
        )
    
    db = get_database()
    result = await db.workspaces.update_many(
        {}, 
        {"$set": {"admin_id": ObjectId(current_user.id)}}
    )
    
    return {
        "message": f"Successfully made user {current_user.id} admin of {result.modified_count} workspaces",
        "modified_count": result.modified_count
    }

@router.get("/{workspace_id}", response_model=Workspace)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get workspace by ID"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    db = get_database()
    workspace_data = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    
    if not workspace_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    workspace_data["_id"] = str(workspace_data["_id"])
    workspace_data["admin_id"] = str(workspace_data["admin_id"])
    workspace_data["member_ids"] = [str(member_id) for member_id in workspace_data.get("member_ids", [])]
    
    # Get admin details
    admin_data = await db.users.find_one({"_id": ObjectId(workspace_data["admin_id"])})
    if admin_data:
        workspace_data["admin"] = {
            "id": str(admin_data["_id"]),
            "email": admin_data["email"],
            "full_name": admin_data["full_name"],
            "is_active": admin_data["is_active"]
        }
    
    return Workspace(**workspace_data)

@router.put("/{workspace_id}", response_model=Workspace)
async def update_workspace(
    workspace_id: str,
    workspace_update: WorkspaceUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update workspace (admin only)"""
    logger.info(f"Update workspace request from user {current_user.id} for workspace {workspace_id}")
    
    # Only workspace admins can update settings
    is_admin = await verify_workspace_admin(current_user, workspace_id)
    logger.info(f"Admin check result: {is_admin} for user {current_user.id} in workspace {workspace_id}")
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only workspace administrators can update workspace settings. User {current_user.id} is not admin of workspace {workspace_id}"
        )
    
    db = get_database()
    
    # Update workspace
    update_dict = {k: v for k, v in workspace_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.workspaces.update_one(
        {"_id": ObjectId(workspace_id)},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return await get_workspace(workspace_id, current_user)

@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete workspace (admin only)"""
    # Only workspace admins can delete workspace
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can delete workspace"
        )
    
    db = get_database()
    
    # Delete workspace and related data
    await db.workspaces.delete_one({"_id": ObjectId(workspace_id)})
    await db.chats.delete_many({"workspace_id": ObjectId(workspace_id)})
    await db.documents.delete_many({"workspace_id": ObjectId(workspace_id)})
    await db.phone_numbers.delete_many({"workspace_id": ObjectId(workspace_id)})
    
    # Remove workspace from all users
    await db.users.update_many(
        {"workspaces": workspace_id},
        {"$pull": {"workspaces": workspace_id}}
    )
    
    return {"message": "Workspace deleted successfully"}

@router.post("/{workspace_id}/members")
async def add_member_to_workspace(
    workspace_id: str,
    member_email: str,
    current_user: User = Depends(get_current_active_user)
):
    """Add member to workspace (admin only)"""
    # Only workspace admins can add members
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can add members"
        )
    
    db = get_database()
    workspace_data = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    
    # Find user by email
    user_data = await db.users.find_one({"email": member_email})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    member_id = ObjectId(user_data["_id"])
    
    # Check if user is already a member
    if member_id in workspace_data.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace"
        )
    
    # Add user to workspace
    await db.workspaces.update_one(
        {"_id": ObjectId(workspace_id)},
        {"$push": {"member_ids": member_id}}
    )
    
    # Add workspace to user's workspace list
    await db.users.update_one(
        {"_id": member_id},
        {"$push": {"workspaces": workspace_id}}
    )
    
    return {"message": "Member added successfully"}

@router.delete("/{workspace_id}/members/{member_id}")
async def remove_member_from_workspace(
    workspace_id: str,
    member_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Remove member from workspace (admin only)"""
    # Only workspace admins can remove members
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can remove members"
        )
    
    db = get_database()
    
    # Remove user from workspace
    await db.workspaces.update_one(
        {"_id": ObjectId(workspace_id)},
        {"$pull": {"member_ids": ObjectId(member_id)}}
    )
    
    # Remove workspace from user's workspace list
    await db.users.update_one(
        {"_id": ObjectId(member_id)},
        {"$pull": {"workspaces": workspace_id}}
    )
    
    return {"message": "Member removed successfully"}

@router.get("/{workspace_id}/members")
async def get_workspace_members(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all members of a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    db = get_database()
    workspace_data = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    
    if not workspace_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Get member details
    members = []
    for member_id in workspace_data.get("member_ids", []):
        user_data = await db.users.find_one({"_id": member_id})
        if user_data:
            user_data["_id"] = str(user_data["_id"])
            members.append({
                "id": user_data["_id"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "is_active": user_data["is_active"],
                "created_at": user_data["created_at"],
                "joined_at": user_data.get("joined_at", user_data["created_at"])
            })
    
    return members