from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import datetime, timedelta
from app.models.user import User
from app.auth.auth_handler import get_current_active_user, verify_workspace_access, verify_workspace_admin
from app.services.excel_export_service import excel_export_service
from app.services.export_scheduler import export_scheduler
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/manual/{workspace_id}")
async def generate_manual_export(
    workspace_id: str,
    email: str = Query(..., description="Email address to send the export"),
    hours: int = Query(24, description="Number of hours to include in export", ge=1, le=168),
    current_user: User = Depends(get_current_active_user)
):
    """Generate manual Excel export for a workspace"""
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
        
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Generate export
        result = await export_scheduler.trigger_manual_export(workspace_id, email)
        
        return {
            "success": True,
            "message": f"Export generated and sent to {email}",
            "workspace_id": workspace_id,
            "hours_included": hours,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Manual export generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate export"
        )

@router.get("/statistics/{workspace_id}")
async def get_export_statistics(
    workspace_id: str,
    days: int = Query(7, description="Number of days to include in statistics", ge=1, le=30),
    current_user: User = Depends(get_current_active_user)
):
    """Get export statistics for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    try:
        stats = await excel_export_service.get_export_statistics(workspace_id, days)
        return {
            "workspace_id": workspace_id,
            "statistics": stats,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get export statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export statistics"
        )

@router.get("/scheduler/status")
async def get_export_scheduler_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of export scheduler"""
    try:
        status = export_scheduler.get_scheduler_status()
        return {
            "scheduler_status": status,
            "export_frequency": f"Every {status.get('export_interval', 15)} minutes",
            "next_exports": [
                job for job in status.get("jobs", []) 
                if job.get("id") == "whatsapp_export"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get export scheduler status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scheduler status"
        )

@router.post("/test-email")
async def test_email_configuration(
    workspace_id: str,
    test_email: str = Query(..., description="Email address to test"),
    current_user: User = Depends(get_current_active_user)
):
    """Test email configuration for a workspace"""
    if not await verify_workspace_admin(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace administrators can test email configuration"
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
        import smtplib
        from email.mime.text import MIMEText
        from app.config import settings
        
        msg = MIMEText("This is a test email from WhatsApp AI Automation System Excel Export Service.")
        msg['Subject'] = f"Test Email - WhatsApp Export System"
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

@router.get("/logs/{workspace_id}")
async def get_export_logs(
    workspace_id: str,
    limit: int = Query(20, description="Number of logs to return", ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Get export logs for a workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    try:
        from app.database import get_database
        db = get_database()
        
        # Get export logs
        export_logs = await db.export_logs.find({
            "workspace_id": workspace_id
        }).sort("export_timestamp", -1).limit(limit).to_list(None)
        
        # Get system logs related to exports
        system_logs = await db.system_logs.find({
            "service": "excel_export_scheduler"
        }).sort("timestamp", -1).limit(limit).to_list(None)
        
        return {
            "workspace_id": workspace_id,
            "export_logs": [
                {
                    "export_timestamp": log["export_timestamp"].isoformat(),
                    "export_type": log["export_type"],
                    "created_at": log["created_at"].isoformat()
                }
                for log in export_logs
            ],
            "system_logs": [
                {
                    "event_type": log["event_type"],
                    "message": log["message"],
                    "timestamp": log["timestamp"].isoformat()
                }
                for log in system_logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get export logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export logs"
        )

@router.post("/trigger-now")
async def trigger_export_now(
    current_user: User = Depends(get_current_active_user)
):
    """Manually trigger export for all workspaces (admin only)"""
    try:
        # Only allow global admins to trigger system-wide export
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system administrators can trigger system-wide exports"
            )
        
        # Trigger the export job
        await excel_export_service.export_all_workspace_messages()
        
        return {
            "success": True,
            "message": "Export triggered successfully for all workspaces",
            "triggered_at": datetime.utcnow().isoformat(),
            "triggered_by": current_user.email
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger manual export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger export"
        )