from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.database import get_database
from app.models.user import TokenData, User
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token bearer
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    if not email or not password:
        return None
        
    db = get_database()
    user_data = await db.users.find_one({"email": email.lower().strip()})
    
    if not user_data:
        return None
    
    if not user_data.get("is_active", True):
        return None
    
    if not verify_password(password, user_data["hashed_password"]):
        return None
    
    user_data["_id"] = str(user_data["_id"])
    return User(**user_data)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    db = get_database()
    user_data = await db.users.find_one({"email": token_data.email})
    
    if user_data is None:
        raise credentials_exception
    
    user_data["_id"] = str(user_data["_id"])
    # Ensure is_admin field is included
    if "is_admin" not in user_data:
        user_data["is_admin"] = False
    
    return User(**user_data)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def verify_workspace_access(user: User, workspace_id: str) -> bool:
    """Verify if user has access to workspace"""
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    
    if not workspace:
        return False
    
    # Check if user is admin or member
    if str(workspace["admin_id"]) == user.id:
        return True
    
    if user.id in [str(member_id) for member_id in workspace.get("member_ids", [])]:
        return True
    
    return False

async def verify_workspace_admin(user: User, workspace_id: str) -> bool:
    """Verify if user is admin of workspace"""
    logger.info(f"Verifying admin access for user {user.id} in workspace {workspace_id}")
    
    # Check if user is global admin first
    if getattr(user, 'is_admin', False):
        logger.info(f"User {user.id} is global admin, granting workspace admin access")
        return True
    
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    
    if not workspace:
        logger.warning(f"Workspace {workspace_id} not found")
        return False
    
    # Check if user is admin
    is_admin = str(workspace["admin_id"]) == user.id
    logger.info(f"Admin check: workspace admin_id={workspace['admin_id']}, user_id={user.id}, is_admin={is_admin}")
    return is_admin

async def get_user_role_in_workspace(user: User, workspace_id: str) -> str:
    """Get user role in workspace (admin, member, or none)"""
    db = get_database()
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    
    if not workspace:
        return "none"
    
    if str(workspace["admin_id"]) == user.id:
        return "admin"
    
    if user.id in [str(member_id) for member_id in workspace.get("member_ids", [])]:
        return "member"
    
    return "none"