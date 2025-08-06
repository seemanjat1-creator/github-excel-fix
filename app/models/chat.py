from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ChatStatus(str, Enum):
    ACTIVE = "active"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CLOSED = "closed"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"

class MessageDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"

class MessageBase(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    direction: MessageDirection
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}

class MessageCreate(MessageBase):
    pass

class MessageInDB(MessageBase):
    id: str = Field(alias="_id")
    chat_id: str
    is_ai_generated: bool = False

class Message(MessageBase):
    id: str = Field(alias="_id")
    chat_id: str
    is_ai_generated: bool = False

class ChatBase(BaseModel):
    customer_phone: str
    customer_name: Optional[str] = None
    status: ChatStatus = ChatStatus.ACTIVE
    ai_enabled: bool = True
    workflow_progress: Dict[str, Any] = {}
    summary: Optional[str] = None
    tags: List[str] = []

class ChatCreate(ChatBase):
    workspace_id: str
    phone_number: str

class ChatUpdate(BaseModel):
    customer_name: Optional[str] = None
    status: Optional[ChatStatus] = None
    ai_enabled: Optional[bool] = None
    workflow_progress: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None

class ChatInDB(ChatBase):
    id: str = Field(alias="_id")
    workspace_id: str
    phone_number: str
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

class Chat(ChatBase):
    id: str = Field(alias="_id")
    workspace_id: str
    phone_number: str
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    messages: List[Message] = []

class ChatSummary(BaseModel):
    chat_id: str
    customer_phone: str
    customer_name: Optional[str]
    summary: str
    status: ChatStatus
    qualified_at: Optional[datetime]
    total_messages: int
    created_at: datetime