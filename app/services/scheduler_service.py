import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.services.excel_report_service import excel_report_service
from app.services.message_queue import message_queue
from app.config import settings
from typing import Dict, Any
logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def start(self):
        """Start the scheduler with all background tasks"""
        try:
            logger.info("Starting scheduler service")
            
            # Excel report generation every 15 minutes
            self.scheduler.add_job(
                func=self._safe_excel_report_job,
                trigger=IntervalTrigger(minutes=15),
                id='excel_reports',
                name='Generate Excel Reports',
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300  # 5 minutes grace time
            )
            
            # Message queue cleanup daily at 2 AM
            self.scheduler.add_job(
                func=self._safe_cleanup_job,
                trigger=CronTrigger(hour=2, minute=0),
                id='queue_cleanup',
                name='Cleanup Old Messages',
                max_instances=1
            )
            
            # Health check every 5 minutes
            self.scheduler.add_job(
                func=self._safe_health_check_job,
                trigger=IntervalTrigger(minutes=5),
                id='health_check',
                name='System Health Check',
                max_instances=1
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Scheduler started successfully with all jobs")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler"""
        try:
            if self.is_running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    async def _safe_excel_report_job(self):
        """Safely execute Excel report generation with error handling"""
        try:
            logger.info("Starting scheduled Excel report generation")
            start_time = datetime.utcnow()
            
            await excel_report_service.generate_workspace_reports()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Excel report generation completed in {execution_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Scheduled Excel report generation failed: {e}")
            # Log to database for monitoring
            await self._log_job_failure("excel_reports", str(e))
    
    async def _safe_cleanup_job(self):
        """Safely execute message queue cleanup"""
        try:
            logger.info("Starting scheduled message queue cleanup")
            
            await message_queue.cleanup_old_messages(days=7)
            
            logger.info("Message queue cleanup completed")
            
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")
            await self._log_job_failure("queue_cleanup", str(e))
    
    async def _safe_health_check_job(self):
        """Perform system health checks"""
        try:
            # Check message queue health
            queue_stats = await message_queue.get_queue_stats()
            
            # Log health metrics
            logger.info(f"System health check - Queue length: {queue_stats.get('queue_length', 0)}, "
                       f"Success rate: {queue_stats.get('success_rate', 0)}%")
            
            # Alert if queue is backing up
            queue_length = queue_stats.get('queue_length', 0)
            if queue_length > 100:
                logger.warning(f"Message queue backing up: {queue_length} messages pending")
            
            # Alert if success rate is low
            success_rate = queue_stats.get('success_rate', 100)
            if success_rate < 90:
                logger.warning(f"Low message processing success rate: {success_rate}%")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _log_job_failure(self, job_id: str, error: str):
        """Log job failure to database for monitoring"""
        try:
            from app.database import get_database
            db = get_database()
            
            failure_log = {
                "job_id": job_id,
                "error": error,
                "timestamp": datetime.utcnow(),
                "type": "scheduled_job_failure"
            }
            
            await db.system_logs.insert_one(failure_log)
            
        except Exception as e:
            logger.error(f"Failed to log job failure: {e}")
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        if not self.is_running:
            return {"status": "stopped", "jobs": []}
        
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
            "scheduler_state": self.scheduler.state
        }
    
    async def trigger_manual_report(self, workspace_id: str, email: str):
        """Manually trigger report generation for a workspace"""
        try:
            from app.database import get_database
            db = get_database()
            
            workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")
            
            # Generate report for last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            excel_file_path = await excel_report_service.generate_manual_report(
                workspace_id, start_time, end_time, email
            )
            
            return {
                "success": True,
                "message": "Manual report generated and sent successfully",
                "file_path": excel_file_path
            }
            
        except Exception as e:
            logger.error(f"Manual report generation failed: {e}")
            raise

# Global scheduler instance
scheduler_service = SchedulerService()