from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageQueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class MessageQueueItem(BaseModel):
    message_id: str
    phone_number: str
    from_phone: str
    content: str
    message_type: str = "text"
    status: MessageQueueStatus = MessageQueueStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
    error_log: List[Dict[str, Any]] = []
    processing_time: Optional[float] = None
    completed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None

class QueueStats(BaseModel):
    queue_length: int
    status_counts: Dict[str, int]
    avg_processing_time: float
    messages_last_hour: int
    success_rate: float

class SystemHealth(BaseModel):
    system_status: str
    timestamp: str
    issues: List[str]
    components: Dict[str, Any]