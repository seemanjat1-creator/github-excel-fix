from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class PhoneStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class PhoneNumberBase(BaseModel):
    phone_number: str
    display_name: Optional[str] = None
    status: PhoneStatus = PhoneStatus.DISCONNECTED
    qr_code: Optional[str] = None
    webhook_url: Optional[str] = None

class PhoneNumberCreate(PhoneNumberBase):
    workspace_id: str

class PhoneNumberUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[PhoneStatus] = None
    qr_code: Optional[str] = None
    webhook_url: Optional[str] = None

class PhoneNumberInDB(PhoneNumberBase):
    id: str = Field(alias="_id")
    workspace_id: str
    created_at: datetime
    updated_at: datetime
    last_connected_at: Optional[datetime] = None

class PhoneNumber(PhoneNumberBase):
    id: str = Field(alias="_id")
    workspace_id: str
    created_at: datetime
    updated_at: datetime
    last_connected_at: Optional[datetime] = None