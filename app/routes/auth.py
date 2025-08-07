from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.models.user import User, UserCreate, UserLogin, Token
from app.auth.auth_handler import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user
)
from app.database import get_database
from app.config import settings
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=User)
async def register(user: UserCreate):
    """Register new user"""
    db = get_database()
    
    # Validate input
    if not user.email or not user.password or not user.full_name:
        raise HTTPException(
            status_code=400,
            detail="Email, password, and full name are required"
        )
    
    if len(user.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )
    
    if len(user.full_name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Full name must be at least 2 characters"
        )
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email.lower().strip()})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    user_dict = user.dict()
    user_dict["email"] = user.email.lower().strip()
    user_dict["full_name"] = user.full_name.strip()
    user_dict["hashed_password"] = get_password_hash(user.password)
    del user_dict["password"]
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    user_dict["workspaces"] = []

    # ✅ Auto-make first registered user an admin
    existing_admins = await db.users.count_documents({"is_admin": True})
    if existing_admins == 0:
        user_dict["is_admin"] = True
        logger.info(f"Making first user {user.email} a global admin")
    else:
        user_dict["is_admin"] = False

    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    
    logger.info(f"User registered: {user.email}, is_admin: {user_dict['is_admin']}")
    return User(**user_dict)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    logger.info(f"User info request: {current_user.email}, is_admin: {getattr(current_user, 'is_admin', False)}")
    return current_user

@router.get("/check-admin/{workspace_id}")
async def check_admin_access(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Check if user is admin of workspace"""
    from app.auth.auth_handler import verify_workspace_admin
    is_admin = await verify_workspace_admin(current_user, workspace_id)
    return {
        "is_admin": is_admin, 
        "user_id": current_user.id,
        "is_global_admin": getattr(current_user, 'is_admin', False),
        "workspace_id": workspace_id
    }

@router.post("/logout")
async def logout():
    """Logout user (client should remove token)"""
    return {"message": "Successfully logged out"}
