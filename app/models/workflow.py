from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class WorkflowStepType(str, Enum):
    QUESTION = "question"
    INFORMATION = "information"
    CONDITION = "condition"
    ACTION = "action"

class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class WorkflowStepBase(BaseModel):
    step_number: int
    title: str
    description: str
    step_type: WorkflowStepType = WorkflowStepType.QUESTION
    is_required: bool = True
    keywords: List[str] = []
    expected_response_pattern: Optional[str] = None
    follow_up_questions: List[str] = []

class WorkflowStepCreate(WorkflowStepBase):
    workspace_id: str

class WorkflowStepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    step_type: Optional[WorkflowStepType] = None
    is_required: Optional[bool] = None
    keywords: Optional[List[str]] = None
    expected_response_pattern: Optional[str] = None
    follow_up_questions: Optional[List[str]] = None

class WorkflowStepInDB(WorkflowStepBase):
    id: str = Field(alias="_id")
    workspace_id: str
    created_at: datetime
    updated_at: datetime

class WorkflowStep(WorkflowStepBase):
    id: str = Field(alias="_id")
    workspace_id: str
    created_at: datetime
    updated_at: datetime

class ChatWorkflowProgress(BaseModel):
    chat_id: str
    workspace_id: str
    current_step: int = 1
    completed_steps: List[int] = []
    step_responses: Dict[str, Any] = {}
    is_qualified: bool = False
    needs_human_help: bool = False
    qualification_score: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class WorkflowAnalysis(BaseModel):
    step_completed: bool
    confidence_score: float
    extracted_info: Dict[str, Any]
    next_step: Optional[int]
    needs_clarification: bool = False
    suggested_response: Optional[str] = None