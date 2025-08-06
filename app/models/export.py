from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ExportType(str, Enum):
    WHATSAPP_MESSAGES = "whatsapp_messages"
    CHAT_SUMMARIES = "chat_summaries"
    QUALIFIED_LEADS = "qualified_leads"

class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportLogBase(BaseModel):
    workspace_id: str
    export_type: ExportType
    export_timestamp: datetime
    message_count: int = 0
    file_path: Optional[str] = None
    email_sent_to: Optional[str] = None
    status: ExportStatus = ExportStatus.COMPLETED
    error_message: Optional[str] = None

class ExportLogCreate(ExportLogBase):
    pass

class ExportLogInDB(ExportLogBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

class ExportLog(ExportLogBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

class ExportRequest(BaseModel):
    workspace_id: str
    email: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    export_type: ExportType = ExportType.WHATSAPP_MESSAGES

class ExportStatistics(BaseModel):
    workspace_id: str
    total_exports: int
    successful_exports: int
    failed_exports: int
    last_export_date: Optional[datetime]
    average_message_count: float
    daily_breakdown: Dict[str, int]

class SystemExportStatus(BaseModel):
    scheduler_running: bool
    export_interval_minutes: int
    next_export_time: Optional[datetime]
    total_workspaces: int
    configured_workspaces: int
    last_export_summary: Dict[str, Any]