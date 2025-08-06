from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import datetime, timedelta
from app.models.user import User
from app.auth.auth_handler import get_current_active_user, verify_workspace_access
from app.services.excel_report_service import excel_report_service
from app.services.scheduler_service import scheduler_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/generate/{workspace_id}")
async def generate_manual_report(
    workspace_id: str,
    email: str = Query(..., description="Email address to send the report"),
    hours: int = Query(24, description="Number of hours to include in report", ge=1, le=168),
    current_user: User = Depends(get_current_active_user)
):
    """Generate manual Excel report for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    try:
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Generate report
        result = await scheduler_service.trigger_manual_report(workspace_id, email)
        
        return {
            "success": True,
            "message": f"Report generated and sent to {email}",
            "workspace_id": workspace_id,
            "hours_included": hours,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Manual report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )

@router.get("/history/{workspace_id}")
async def get_report_history(
    workspace_id: str,
    limit: int = Query(10, description="Number of reports to return", ge=1, le=50),
    current_user: User = Depends(get_current_active_user)
):
    """Get report generation history for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    try:
        history = await excel_report_service.get_report_history(workspace_id, limit)
        return {
            "workspace_id": workspace_id,
            "reports": history,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get report history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report history"
        )

@router.get("/schedule/status")
async def get_schedule_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of scheduled report generation"""
    try:
        status = scheduler_service.get_job_status()
        return {
            "scheduler_status": status,
            "report_frequency": "Every 15 minutes",
            "next_reports": [
                job for job in status.get("jobs", []) 
                if job.get("id") == "excel_reports"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get schedule status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schedule status"
        )

@router.post("/test-email")
async def test_email_configuration(
    workspace_id: str,
    test_email: str = Query(..., description="Email address to test"),
    current_user: User = Depends(get_current_active_user)
):
    """Test email configuration for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    try:
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, test_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Send test email
        from app.services.excel_report_service import excel_report_service
        import smtplib
        from email.mime.text import MIMEText
        from app.config import settings
        
        msg = MIMEText("This is a test email from WhatsApp AI Automation System.")
        msg['Subject'] = f"Test Email - WhatsApp Reports"
        msg['From'] = settings.smtp_username
        msg['To'] = test_email
        
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {
            "success": True,
            "message": f"Test email sent successfully to {test_email}",
            "workspace_id": workspace_id
        }
        
    except Exception as e:
        logger.error(f"Email test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email test failed: {str(e)}"
        )