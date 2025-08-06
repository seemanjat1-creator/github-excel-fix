from pydantic import BaseModel, Field,EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from app.auth.auth_handler import get_current_user  # Adjust import as per your project

class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class AISettings(BaseModel):
    # Basic AI Configuration
    system_prompt: str = "You are a helpful WhatsApp AI assistant for customer support."
    
    # Style and Tone Settings
    tone: str = "polite"  # polite, friendly, professional, casual
    response_length: str = "short"  # short, medium, long
    language: str = "english"  # english, spanish, french, german, hindi, etc.
    
    # Additional Options
    include_emojis: bool = True
    formal_style: bool = False
    friendly_approach: bool = True
    detailed_responses: bool = False
    
    # Advanced Features
    reply_suggestions: bool = True
    personalization: bool = True
    fallback_messaging: bool = True
    context_awareness: bool = True
    
    # Custom Instructions
    custom_instructions: Optional[str] = None
    greeting_message: Optional[str] = None
    fallback_message: Optional[str] = "I'm sorry, I didn't understand that. Could you please rephrase your question?"
    
    # Business Context
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_description: Optional[str] = None
    
    # Response Behavior
    max_response_tokens: int = 150
    temperature: float = 0.7
    use_knowledge_base: bool = True
    escalate_to_human: bool = True

class WorkflowStep(BaseModel):
    step_number: int
    description: str
    is_required: bool = True
    is_completed: bool = False

class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    ai_settings: AISettings = AISettings()
    workflow_steps: List[WorkflowStep] = []

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkspaceStatus] = None
    ai_settings: Optional[AISettings] = None
    workflow_steps: Optional[List[WorkflowStep]] = None

class WorkspaceInDB(WorkspaceBase):
    id: str = Field(alias="_id")
    admin_id: str
    member_ids: List[str] = []
    created_at: datetime
    updated_at: datetime

class Workspace(WorkspaceBase):
    id: str = Field(alias="_id")
    admin_id: str
    member_ids: List[str] = []
    created_at: datetime
    updated_at: datetime

class WorkspaceInvite(BaseModel):
    email: str
    workspace_id: str


class AddMemberRequest(BaseModel):
    email: EmailStr
