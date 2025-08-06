import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.services.excel_export_service import excel_export_service
from bson import ObjectId
from app.config import settings

logger = logging.getLogger(__name__)

class ExportScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.export_interval = getattr(settings, 'export_interval_minutes', 15)
    
    async def start(self):
        """Start the export scheduler"""
        try:
            logger.info("Starting export scheduler service")
            
            # WhatsApp message export every X minutes (configurable)
            self.scheduler.add_job(
                func=self._safe_export_job,
                trigger=IntervalTrigger(minutes=self.export_interval),
                id='whatsapp_export',
                name='WhatsApp Message Export',
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300  # 5 minutes grace time
            )
            
            # File cleanup daily at 3 AM
            self.scheduler.add_job(
                func=self._safe_cleanup_job,
                trigger=CronTrigger(hour=3, minute=0),
                id='file_cleanup',
                name='Export File Cleanup',
                max_instances=1
            )
            
            # Export health check every hour
            self.scheduler.add_job(
                func=self._safe_health_check_job,
                trigger=IntervalTrigger(hours=1),
                id='export_health_check',
                name='Export System Health Check',
                max_instances=1
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Export scheduler started successfully - running every {self.export_interval} minutes")
            
        except Exception as e:
            logger.error(f"Failed to start export scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the export scheduler"""
        try:
            if self.is_running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("Export scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop export scheduler: {e}")
    
    async def _safe_export_job(self):
        """Safely execute WhatsApp message export with error handling"""
        try:
            logger.info("Starting scheduled WhatsApp message export")
            start_time = datetime.utcnow()
            
            await excel_export_service.export_all_workspace_messages()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"WhatsApp export completed in {execution_time:.2f} seconds")
            
            # Log successful export
            await self._log_export_event("success", f"Export completed in {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Scheduled WhatsApp export failed: {e}")
            await self._log_export_event("error", str(e))
    
    async def _safe_cleanup_job(self):
        """Safely execute file cleanup"""
        try:
            logger.info("Starting scheduled file cleanup")
            
            await excel_export_service._cleanup_old_files()
            
            logger.info("File cleanup completed")
            await self._log_export_event("cleanup", "File cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")
            await self._log_export_event("cleanup_error", str(e))
    
    async def _safe_health_check_job(self):
        """Perform export system health checks"""
        try:
            # Check if export directory exists and is writable
            import os
            export_dir = "exports"
            
            if not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)
            
            # Test file write
            test_file = os.path.join(export_dir, "health_check.tmp")
            with open(test_file, 'w') as f:
                f.write("health check")
            os.remove(test_file)
            
            # Check SMTP configuration
            smtp_configured = all([
                settings.smtp_server,
                settings.smtp_port,
                settings.smtp_username,
                settings.smtp_password
            ])
            
            if not smtp_configured:
                logger.warning("SMTP configuration incomplete")
            
            # Check workspace email configurations
            from app.database import get_database
            db = get_database()
            workspaces = await db.workspaces.find({"status": "active"}).to_list(None)
            
            configured_workspaces = 0
            for workspace in workspaces:
                workspace_id = str(workspace["_id"])
                email_key = f"WORKSPACE_{workspace_id}_EMAIL"
                if os.getenv(email_key):
                    configured_workspaces += 1
            
            logger.info(f"Export health check - {configured_workspaces}/{len(workspaces)} workspaces have email configured")
            
            await self._log_export_event(
                "health_check", 
                f"System healthy - {configured_workspaces}/{len(workspaces)} workspaces configured"
            )
            
        except Exception as e:
            logger.error(f"Export health check failed: {e}")
            await self._log_export_event("health_check_error", str(e))
    
    async def _log_export_event(self, event_type: str, message: str):
        """Log export events to database"""
        try:
            from app.database import get_database
            db = get_database()
            
            event_log = {
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.utcnow(),
                "service": "excel_export_scheduler"
            }
            
            await db.system_logs.insert_one(event_log)
            
        except Exception as e:
            logger.error(f"Failed to log export event: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get status of export scheduler"""
        if not self.is_running:
            return {"status": "stopped", "jobs": [], "export_interval": self.export_interval}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs,
            "export_interval": self.export_interval,
            "scheduler_state": self.scheduler.state
        }
    
    async def trigger_manual_export(self, workspace_id: str, email: str):
        """Manually trigger export for a workspace"""
        try:
            from app.database import get_database
            db = get_database()
            
            workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")
            
            # Generate export for last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            excel_file_path = await excel_export_service.manual_export(
                workspace_id, start_time, end_time, email
            )
            
            await self._log_export_event(
                "manual_export", 
                f"Manual export generated for workspace {workspace_id}, sent to {email}"
            )
            
            return {
                "success": True,
                "message": "Manual export generated and sent successfully",
                "file_path": excel_file_path
            }
            
        except Exception as e:
            logger.error(f"Manual export failed: {e}")
            await self._log_export_event("manual_export_error", str(e))
            raise

# Global scheduler instance
export_scheduler = ExportScheduler()