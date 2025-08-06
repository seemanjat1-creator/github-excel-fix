from typing import List, Optional, Dict, Any
from app.models.workflow import (
    WorkflowStep, WorkflowStepCreate, WorkflowStepUpdate, 
    ChatWorkflowProgress, WorkflowAnalysis, WorkflowStepStatus
)
from app.database import get_database
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WorkflowService:
    async def create_workflow_step(self, step_data: WorkflowStepCreate) -> WorkflowStep:
        """Create new workflow step"""
        db = get_database()
        
        # Get next step number
        existing_steps = await db.workflow_steps.count_documents({
            "workspace_id": ObjectId(step_data.workspace_id)
        })
        
        step_dict = step_data.dict()
        step_dict["workspace_id"] = ObjectId(step_data.workspace_id)
        step_dict["step_number"] = existing_steps + 1
        step_dict["created_at"] = datetime.utcnow()
        step_dict["updated_at"] = datetime.utcnow()
        
        result = await db.workflow_steps.insert_one(step_dict)
        step_dict["_id"] = str(result.inserted_id)
        step_dict["workspace_id"] = step_data.workspace_id
        
        return WorkflowStep(**step_dict)
    
    async def get_workspace_workflow_steps(self, workspace_id: str) -> List[WorkflowStep]:
        """Get all workflow steps for a workspace"""
        db = get_database()
        cursor = db.workflow_steps.find({
            "workspace_id": ObjectId(workspace_id)
        }).sort("step_number", 1)
        
        steps = []
        async for step in cursor:
            step["_id"] = str(step["_id"])
            step["workspace_id"] = workspace_id
            steps.append(WorkflowStep(**step))
        
        return steps
    
    async def get_workflow_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        """Get workflow step by ID"""
        db = get_database()
        step_data = await db.workflow_steps.find_one({"_id": ObjectId(step_id)})
        
        if not step_data:
            return None
        
        step_data["_id"] = str(step_data["_id"])
        step_data["workspace_id"] = str(step_data["workspace_id"])
        
        return WorkflowStep(**step_data)
    
    async def update_workflow_step(self, step_id: str, update_data: WorkflowStepUpdate) -> Optional[WorkflowStep]:
        """Update workflow step"""
        db = get_database()
        
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await db.workflow_steps.update_one(
            {"_id": ObjectId(step_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await self.get_workflow_step_by_id(step_id)
    
    async def delete_workflow_step(self, step_id: str) -> bool:
        """Delete workflow step"""
        db = get_database()
        result = await db.workflow_steps.delete_one({"_id": ObjectId(step_id)})
        return result.deleted_count > 0
    
    async def reorder_workflow_steps(self, workspace_id: str, step_orders: List[dict]) -> bool:
        """Reorder workflow steps"""
        db = get_database()
        
        try:
            for order_data in step_orders:
                await db.workflow_steps.update_one(
                    {"_id": ObjectId(order_data["step_id"])},
                    {"$set": {"step_number": order_data["step_number"], "updated_at": datetime.utcnow()}}
                )
            return True
        except Exception as e:
            logger.error(f"Failed to reorder workflow steps: {e}")
            return False
    
    async def get_chat_workflow_progress(self, chat_id: str) -> Optional[ChatWorkflowProgress]:
        """Get workflow progress for a chat"""
        db = get_database()
        progress_data = await db.chat_workflow_progress.find_one({"chat_id": chat_id})
        
        if not progress_data:
            return None
        
        progress_data["_id"] = str(progress_data["_id"])
        return ChatWorkflowProgress(**progress_data)
    
    async def update_chat_workflow_progress(
        self, 
        chat_id: str, 
        workspace_id: str, 
        analysis: WorkflowAnalysis,
        current_step: int
    ) -> ChatWorkflowProgress:
        """Update workflow progress for a chat"""
        db = get_database()
        
        # Get existing progress or create new
        progress = await self.get_chat_workflow_progress(chat_id)
        
        if not progress:
            progress_data = {
                "chat_id": chat_id,
                "workspace_id": workspace_id,
                "current_step": current_step,
                "completed_steps": [],
                "step_responses": {},
                "is_qualified": False,
                "needs_human_help": False,
                "qualification_score": 0.0,
                "last_updated": datetime.utcnow()
            }
            
            result = await db.chat_workflow_progress.insert_one(progress_data)
            progress_data["_id"] = str(result.inserted_id)
            progress = ChatWorkflowProgress(**progress_data)
        
        # Update progress based on analysis
        update_data = {
            "last_updated": datetime.utcnow(),
            "qualification_score": analysis.confidence_score
        }
        
        if analysis.step_completed:
            if current_step not in progress.completed_steps:
                update_data["$push"] = {"completed_steps": current_step}
            
            # Update step responses
            step_responses = progress.step_responses.copy()
            step_responses[str(current_step)] = analysis.extracted_info
            update_data["step_responses"] = step_responses
            
            # Move to next step if available
            if analysis.next_step:
                update_data["current_step"] = analysis.next_step
        
        # Check if needs human help
        if analysis.confidence_score < 0.5 or analysis.needs_clarification:
            update_data["needs_human_help"] = True
        
        # Check qualification
        workflow_steps = await self.get_workspace_workflow_steps(workspace_id)
        required_steps = [step.step_number for step in workflow_steps if step.is_required]
        completed_required = [step for step in progress.completed_steps if step in required_steps]
        
        if len(completed_required) >= len(required_steps) * 0.8:  # 80% completion threshold
            update_data["is_qualified"] = True
        
        await db.chat_workflow_progress.update_one(
            {"chat_id": chat_id},
            {"$set": update_data}
        )
        
        return await self.get_chat_workflow_progress(chat_id)
    
    async def analyze_message_against_workflow(
        self, 
        message: str, 
        workspace_id: str, 
        current_step: int,
        chat_history: List[dict] = None
    ) -> WorkflowAnalysis:
        """Analyze message against current workflow step"""
        from app.services.openai_service import openai_service
        
        # Get current workflow step
        workflow_steps = await self.get_workspace_workflow_steps(workspace_id)
        current_step_data = next((step for step in workflow_steps if step.step_number == current_step), None)
        
        if not current_step_data:
            return WorkflowAnalysis(
                step_completed=False,
                confidence_score=0.0,
                extracted_info={},
                next_step=None,
                needs_clarification=True,
                suggested_response="I'm not sure how to help with that. Let me connect you with a human agent."
            )
        
        # Use OpenAI to analyze the message
        analysis = await openai_service.analyze_workflow_step_completion(
            message=message,
            step_data=current_step_data,
            chat_history=chat_history or [],
            all_workflow_steps=workflow_steps
        )
        
        return analysis

workflow_service = WorkflowService()