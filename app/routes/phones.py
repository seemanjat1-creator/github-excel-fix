from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.user import User
from app.models.phone_number import PhoneNumber, PhoneNumberCreate, PhoneNumberUpdate, PhoneStatus
from app.auth.auth_handler import get_current_active_user, verify_workspace_access, verify_workspace_admin
from app.services.whatsapp_service import whatsapp_service
from app.database import get_database
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/workspace/{workspace_id}", response_model=List[PhoneNumber])
async def get_workspace_phones(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all phone numbers for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    db = get_database()
    cursor = db.phone_numbers.find({"workspace_id": ObjectId(workspace_id)})
    phones = []
    
    async for phone in cursor:
        phone["_id"] = str(phone["_id"])
        phone["workspace_id"] = workspace_id
        phones.append(PhoneNumber(**phone))
    
    return phones

@router.post("/", response_model=PhoneNumber)
async def add_phone_number(
    phone_data: PhoneNumberCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Add new phone number to workspace"""
    logger.info(f"Add phone request from user {current_user.id} for workspace {phone_data.workspace_id}")
    logger.info(f"User admin status: is_admin={getattr(current_user, 'is_admin', False)}")
    
    # Only workspace admins can add phone numbers
    is_admin = await verify_workspace_admin(current_user, phone_data.workspace_id)
    logger.info(f"Admin check result: {is_admin} for user {current_user.id} in workspace {phone_data.workspace_id}")
    
    if not is_admin:
        logger.error(f"Access denied: User {current_user.id} (global_admin={getattr(current_user, 'is_admin', False)}) is not admin of workspace {phone_data.workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only workspace administrators can add phone numbers. User {current_user.id} is not admin of workspace {phone_data.workspace_id}"
        )
    
    db = get_database()
    
    # Validate phone number
    if not phone_data.phone_number or len(phone_data.phone_number.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid phone number is required"
        )
    
    # Clean phone number
    clean_phone = phone_data.phone_number.strip()
    if not clean_phone.startswith('+'):
        clean_phone = '+' + clean_phone
    
    # Check if phone number already exists
    existing_phone = await db.phone_numbers.find_one({"phone_number": clean_phone})
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already exists"
        )
    
    # Check workspace phone limit (max 2 per workspace)
    phone_count = await db.phone_numbers.count_documents({"workspace_id": ObjectId(phone_data.workspace_id)})
    if phone_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 2 phone numbers allowed per workspace"
        )
    
    phone_dict = phone_data.dict()
    phone_dict["phone_number"] = clean_phone
    phone_dict["display_name"] = phone_data.display_name.strip() if phone_data.display_name else None
    phone_dict["workspace_id"] = ObjectId(phone_data.workspace_id)
    phone_dict["created_at"] = datetime.utcnow()
    phone_dict["updated_at"] = datetime.utcnow()
    
    result = await db.phone_numbers.insert_one(phone_dict)
    phone_dict["_id"] = str(result.inserted_id)
    phone_dict["workspace_id"] = phone_data.workspace_id
    
    return PhoneNumber(**phone_dict)

@router.post("/{phone_id}/connect")
async def connect_phone(
    phone_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Connect phone number to WhatsApp"""
    db = get_database()
    phone_data = await db.phone_numbers.find_one({"_id": ObjectId(phone_id)})
    
    if not phone_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    workspace_id = str(phone_data["workspace_id"])
    # Only workspace admins can connect phone numbers
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can connect phone numbers"
        )
    
    # Request QR code from WhatsApp service
    qr_code = await whatsapp_service.request_qr_code(phone_data["phone_number"])
    
    if qr_code:
        # Update phone status and QR code
        await db.phone_numbers.update_one(
            {"_id": ObjectId(phone_id)},
            {"$set": {
                "status": PhoneStatus.CONNECTING,
                "qr_code": qr_code,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {"message": "QR code generated", "qr_code": qr_code}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate QR code"
        )

@router.post("/{phone_id}/disconnect")
async def disconnect_phone(
    phone_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Disconnect phone number from WhatsApp"""
    db = get_database()
    phone_data = await db.phone_numbers.find_one({"_id": ObjectId(phone_id)})
    
    if not phone_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    workspace_id = str(phone_data["workspace_id"])
    # Only workspace admins can disconnect phone numbers
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can disconnect phone numbers"
        )
    
    # Disconnect from WhatsApp service
    success = await whatsapp_service.disconnect_phone(phone_data["phone_number"])
    
    if success:
        # Update phone status
        await db.phone_numbers.update_one(
            {"_id": ObjectId(phone_id)},
            {"$set": {
                "status": PhoneStatus.DISCONNECTED,
                "qr_code": None,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {"message": "Phone disconnected successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect phone"
        )

@router.get("/{phone_id}/status")
async def get_phone_status(
    phone_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get phone connection status"""
    db = get_database()
    phone_data = await db.phone_numbers.find_one({"_id": ObjectId(phone_id)})
    
    if not phone_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    workspace_id = str(phone_data["workspace_id"])
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Get real-time status from WhatsApp service
    status = await whatsapp_service.get_connection_status(phone_data["phone_number"])
    
    # Update database if status changed
    if status != phone_data["status"]:
        await whatsapp_service.update_phone_status(phone_data["phone_number"], status)
    
    return {"status": status, "qr_code": phone_data.get("qr_code")}

@router.put("/{phone_id}")
async def update_phone(
    phone_id: str,
    phone_update: PhoneNumberUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update phone number settings"""
    db = get_database()
    phone_data = await db.phone_numbers.find_one({"_id": ObjectId(phone_id)})
    
    if not phone_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    workspace_id = str(phone_data["workspace_id"])
    # Only workspace admins can update phone numbers
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can update phone numbers"
        )
    
    update_dict = {k: v for k, v in phone_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.phone_numbers.update_one(
        {"_id": ObjectId(phone_id)},
        {"$set": update_dict}
    )
    
    # Get updated phone data
    updated_phone = await db.phone_numbers.find_one({"_id": ObjectId(phone_id)})
    updated_phone["_id"] = str(updated_phone["_id"])
    updated_phone["workspace_id"] = workspace_id
    
    return PhoneNumber(**updated_phone)

@router.delete("/{phone_id}")
async def delete_phone(
    phone_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete phone number"""
    logger.info(f"Delete phone request from user {current_user.id} for phone {phone_id}")
    
    db = get_database()
    phone_data = await db.phone_numbers.find_one({"_id": ObjectId(phone_id)})
    
    if not phone_data:
        logger.warning(f"Phone number {phone_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found"
        )
    
    workspace_id = str(phone_data["workspace_id"])
    phone_number = phone_data["phone_number"]
    
    # Only workspace admins can delete phone numbers
    is_admin = await verify_workspace_admin(current_user, workspace_id)
    logger.info(f"Admin check for user {current_user.id} in workspace {workspace_id}: {is_admin}")
    
    if not is_admin:
        logger.warning(f"User {current_user.id} denied access to delete phone {phone_id} in workspace {workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only workspace administrators can delete phone numbers. User {current_user.id} is not admin of workspace {workspace_id}"
        )
    
    try:
        # Disconnect from WhatsApp first if connected
        if phone_data.get("status") == PhoneStatus.CONNECTED:
            logger.info(f"Disconnecting phone {phone_number} from WhatsApp before deletion")
            disconnect_success = await whatsapp_service.disconnect_phone(phone_number)
            if not disconnect_success:
                logger.warning(f"Failed to disconnect phone {phone_number} from WhatsApp, proceeding with deletion")
        
        # Check if phone is being used in active chats
        active_chats = await db.chats.count_documents({
            "phone_number": phone_number,
            "status": {"$in": ["active", "qualified"]}
        })
        
        if active_chats > 0:
            logger.warning(f"Phone {phone_number} has {active_chats} active chats")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete phone number. It has {active_chats} active chat(s). Please close all chats first."
            )
        
        # Soft delete: Update chats to mark phone as deleted (optional)
        await db.chats.update_many(
            {"phone_number": phone_number},
            {"$set": {"phone_deleted": True, "updated_at": datetime.utcnow()}}
        )
        
        # Hard delete the phone number
        delete_result = await db.phone_numbers.delete_one({"_id": ObjectId(phone_id)})
        
        if delete_result.deleted_count == 0:
            logger.error(f"Failed to delete phone {phone_id} from database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete phone number from database"
            )
        
        # Log the deletion for audit purposes
        audit_log = {
            "action": "phone_deleted",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "workspace_id": workspace_id,
            "phone_id": phone_id,
            "phone_number": phone_number,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "display_name": phone_data.get("display_name"),
                "status": phone_data.get("status"),
                "active_chats_updated": True
            }
        }
        
        await db.audit_logs.insert_one(audit_log)
        logger.info(f"Phone {phone_number} successfully deleted by user {current_user.id} from workspace {workspace_id}")
        
        return {
            "success": True,
            "message": "Phone number successfully deleted from workspace",
            "workspace_id": workspace_id,
            "deleted_phone": phone_number,
            "phone_id": phone_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": {
                "user_id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting phone {phone_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the phone number"
        )

@router.delete("/workspace/{workspace_id}/phone/{phone_number}")
async def delete_phone_by_number(
    workspace_id: str,
    phone_number: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete phone number by workspace ID and phone number"""
    logger.info(f"Delete phone by number request from user {current_user.id} for phone {phone_number} in workspace {workspace_id}")
    
    # Validate inputs
    if not workspace_id or not workspace_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace ID is required"
        )
    
    if not phone_number or not phone_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required"
        )
    
    # Sanitize phone number
    clean_phone = phone_number.strip()
    if not clean_phone.startswith('+'):
        clean_phone = '+' + clean_phone
    
    # Only workspace admins can delete phone numbers
    is_admin = await verify_workspace_admin(current_user, workspace_id)
    logger.info(f"Admin check for user {current_user.id} in workspace {workspace_id}: {is_admin}")
    
    if not is_admin:
        logger.warning(f"User {current_user.id} denied access to delete phone {clean_phone} in workspace {workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only workspace administrators can delete phone numbers. User {current_user.id} is not admin of workspace {workspace_id}"
        )
    
    db = get_database()
    
    # Find the phone number
    phone_data = await db.phone_numbers.find_one({
        "workspace_id": ObjectId(workspace_id),
        "phone_number": clean_phone
    })
    
    if not phone_data:
        logger.warning(f"Phone number {clean_phone} not found in workspace {workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phone number {clean_phone} not found in workspace"
        )
    
    # Use the existing delete function
    phone_id = str(phone_data["_id"])
    return await delete_phone(phone_id, current_user)
    
    # Delete from database
    await db.phone_numbers.delete_one({"_id": ObjectId(phone_id)})
    
    return {"message": "Phone number deleted successfully"}