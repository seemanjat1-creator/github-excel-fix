import os
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.config import settings
from app.database import get_database
from app.services.email_service import email_service
from bson import ObjectId
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import shutil

logger = logging.getLogger(__name__)

class ExcelExportService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.export_dir = "exports"
        self.max_file_age_days = 7
        os.makedirs(self.export_dir, exist_ok=True)
    
    async def export_all_workspace_messages(self):
        """Main export function - exports messages for all workspaces"""
        try:
            logger.info("Starting automated WhatsApp message export")
            
            db = get_database()
            
            # Get all active workspaces
            workspaces = await db.workspaces.find({"status": "active"}).to_list(None)
            
            if not workspaces:
                logger.info("No active workspaces found")
                return
            
            export_summary = {
                "total_workspaces": len(workspaces),
                "successful_exports": 0,
                "failed_exports": 0,
                "total_messages_exported": 0,
                "export_timestamp": datetime.utcnow().isoformat()
            }
            
            # Process each workspace
            for workspace in workspaces:
                try:
                    result = await self._export_workspace_messages(workspace)
                    if result["success"]:
                        export_summary["successful_exports"] += 1
                        export_summary["total_messages_exported"] += result["message_count"]
                    else:
                        export_summary["failed_exports"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to export messages for workspace {workspace['_id']}: {e}")
                    export_summary["failed_exports"] += 1
                    continue
            
            # Log export summary
            logger.info(f"Export completed: {export_summary}")
            
            # Cleanup old files
            await self._cleanup_old_files()
            
        except Exception as e:
            logger.error(f"Excel export process failed: {e}")
            raise
    
    async def _export_workspace_messages(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """Export messages for a specific workspace"""
        workspace_id = str(workspace["_id"])
        workspace_name = workspace["name"]
        
        try:
            logger.info(f"Exporting messages for workspace: {workspace_name} ({workspace_id})")
            
            # Get workspace email configuration
            email_key = f"WORKSPACE_{workspace_id}_EMAIL"
            workspace_email = os.getenv(email_key)
            
            if not workspace_email:
                logger.warning(f"No email configured for workspace {workspace_id} (key: {email_key})")
                return {"success": False, "message_count": 0, "reason": "no_email_configured"}
            
            # Get last export timestamp for this workspace
            last_export_time = await self._get_last_export_timestamp(workspace_id)
            
            # Query messages since last export
            messages = await self._get_workspace_messages_since(workspace_id, last_export_time)
            
            if not messages:
                logger.info(f"No new messages for workspace {workspace_name} since {last_export_time}")
                return {"success": True, "message_count": 0, "reason": "no_new_messages"}
            
            logger.info(f"Found {len(messages)} new messages for workspace {workspace_name}")
            
            # Generate Excel file
            excel_file_path = await self._create_excel_file(messages, workspace_name, workspace_id)
            
            # Send email
            await email_service.send_email_with_attachment(
                recipient_email=workspace_email,
                subject=f"WhatsApp Messages Export - {workspace_name} - {datetime.utcnow().strftime('%Y-%m-%d')}",
                body=self._create_email_body(workspace_name, len(messages)),
                attachment_path=excel_file_path,
                attachment_name=os.path.basename(excel_file_path)
            )
            
            # Update last export timestamp
            await self._update_last_export_timestamp(workspace_id)
            
            # Cleanup file after sending
            if os.path.exists(excel_file_path):
                os.remove(excel_file_path)
                logger.info(f"Cleaned up file: {excel_file_path}")
            
            return {"success": True, "message_count": len(messages), "reason": "exported_successfully"}
            
        except Exception as e:
            logger.error(f"Failed to export messages for workspace {workspace_name}: {e}")
            return {"success": False, "message_count": 0, "reason": f"error: {str(e)}"}
    
    async def _get_last_export_timestamp(self, workspace_id: str) -> datetime:
        """Get the last export timestamp for a workspace"""
        db = get_database()
        
        # Check for last export record
        last_export = await db.export_logs.find_one(
            {"workspace_id": workspace_id, "export_type": "whatsapp_messages"},
            sort=[("export_timestamp", -1)]
        )
        
        if last_export:
            return last_export["export_timestamp"]
        else:
            # If no previous export, start from 15 minutes ago
            return datetime.utcnow() - timedelta(minutes=15)
    
    async def _get_workspace_messages_since(self, workspace_id: str, since_time: datetime) -> List[Dict[str, Any]]:
        """Get all messages for a workspace since the given timestamp"""
        db = get_database()
        
        # Aggregation pipeline to join messages with chats
        pipeline = [
            {
                "$lookup": {
                    "from": "chats",
                    "localField": "chat_id",
                    "foreignField": "_id",
                    "as": "chat"
                }
            },
            {
                "$unwind": "$chat"
            },
            {
                "$match": {
                    "chat.workspace_id": ObjectId(workspace_id),
                    "timestamp": {"$gte": since_time}
                }
            },
            {
                "$sort": {"timestamp": -1}
            }
        ]
        
        messages = []
        async for message in db.messages.aggregate(pipeline):
            messages.append(message)
        
        return messages
    
    async def _create_excel_file(
        self, 
        messages: List[Dict[str, Any]], 
        workspace_name: str,
        workspace_id: str
    ) -> str:
        """Create Excel file from messages data"""
        try:
            # Create workspace directory
            workspace_dir = os.path.join(self.export_dir, self._sanitize_filename(workspace_name))
            os.makedirs(workspace_dir, exist_ok=True)
            
            # Prepare data for Excel
            excel_data = []
            
            for message in messages:
                chat = message.get("chat", {})
                
                # Determine sender and receiver based on message direction
                if message.get("direction") == "incoming":
                    sender_phone = chat.get("customer_phone", "Unknown")
                    receiver_phone = chat.get("phone_number", "Unknown")
                    status = "received"
                else:
                    sender_phone = chat.get("phone_number", "Unknown")
                    receiver_phone = chat.get("customer_phone", "Unknown")
                    
                    # Determine if sent by AI or human
                    if message.get("is_ai_generated", False):
                        status = "sent_via_ai"
                    else:
                        status = "sent_by_human"
                
                excel_data.append({
                    "Sender Phone Number": sender_phone,
                    "Receiver Phone Number": receiver_phone,
                    "Message Content": message.get("content", ""),
                    "Timestamp": message.get("timestamp", datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": status,
                    "Workspace ID": workspace_id
                })
            
            # Create DataFrame with exact column order
            df = pd.DataFrame(excel_data, columns=[
                "Sender Phone Number",
                "Receiver Phone Number", 
                "Message Content",
                "Timestamp",
                "Status",
                "Workspace ID"
            ])
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
            safe_workspace_name = self._sanitize_filename(workspace_name)
            filename = f"{safe_workspace_name}_whatsapp_messages_{timestamp}.xlsx"
            file_path = os.path.join(workspace_dir, filename)
            
            # Create Excel file with formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='WhatsApp Messages', index=False)
                
                # Get workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['WhatsApp Messages']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    # Set width with reasonable limits
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Format headers
                from openpyxl.styles import Font, PatternFill
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
            
            logger.info(f"Excel file created: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to create Excel file: {e}")
            raise
    
    def _create_email_body(self, workspace_name: str, message_count: int) -> str:
        """Create email body for export notification"""
        return f"""
Dear Team,

Please find attached the WhatsApp messages export for workspace "{workspace_name}".

Export Details:
- Workspace: {workspace_name}
- Time Period: Last 15 minutes
- Total Messages: {message_count}
- Export Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

This automated export includes all WhatsApp conversations, AI-generated responses, and customer interactions for the specified time period.

Best regards,
WhatsApp AI Automation System
        """.strip()
    
    async def _update_last_export_timestamp(self, workspace_id: str):
        """Update the last export timestamp for a workspace"""
        db = get_database()
        
        export_log = {
            "workspace_id": workspace_id,
            "export_type": "whatsapp_messages",
            "export_timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        # Upsert the export log
        await db.export_logs.update_one(
            {
                "workspace_id": workspace_id,
                "export_type": "whatsapp_messages"
            },
            {"$set": export_log},
            upsert=True
        )
    
    async def _cleanup_old_files(self):
        """Clean up old export files"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.max_file_age_days)
            deleted_count = 0
            
            if not os.path.exists(self.export_dir):
                return
            
            # Walk through all workspace directories
            for workspace_dir in os.listdir(self.export_dir):
                workspace_path = os.path.join(self.export_dir, workspace_dir)
                
                if not os.path.isdir(workspace_path):
                    continue
                
                # Check files in workspace directory
                for filename in os.listdir(workspace_path):
                    file_path = os.path.join(workspace_path, filename)
                    
                    if os.path.isfile(file_path):
                        # Get file modification time
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff_date:
                            os.remove(file_path)
                            deleted_count += 1
                            logger.info(f"Deleted old export file: {file_path}")
                
                # Remove empty workspace directories
                if not os.listdir(workspace_path):
                    os.rmdir(workspace_path)
                    logger.info(f"Removed empty workspace directory: {workspace_path}")
            
            logger.info(f"Cleanup completed: {deleted_count} old files deleted")
            
        except Exception as e:
            logger.error(f"File cleanup failed: {e}")
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize workspace name for use in filenames"""
        # Remove or replace invalid characters
        sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        # Replace spaces with underscores and convert to lowercase
        sanitized = sanitized.replace(' ', '_').lower()
        # Ensure it's not empty
        return sanitized if sanitized else "workspace"
    
    async def get_export_statistics(self, workspace_id: str, days: int = 7) -> Dict[str, Any]:
        """Get export statistics for a workspace"""
        try:
            db = get_database()
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get export logs
            export_logs = await db.export_logs.find({
                "workspace_id": workspace_id,
                "export_type": "whatsapp_messages",
                "export_timestamp": {"$gte": cutoff_date}
            }).sort("export_timestamp", -1).to_list(None)
            
            # Get message statistics
            pipeline = [
                {
                    "$lookup": {
                        "from": "chats",
                        "localField": "chat_id",
                        "foreignField": "_id",
                        "as": "chat"
                    }
                },
                {
                    "$unwind": "$chat"
                },
                {
                    "$match": {
                        "chat.workspace_id": ObjectId(workspace_id),
                        "timestamp": {"$gte": cutoff_date}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                            "status": {
                                "$cond": {
                                    "if": {"$eq": ["$direction", "incoming"]},
                                    "then": "received",
                                    "else": {
                                        "$cond": {
                                            "if": {"$eq": ["$is_ai_generated", True]},
                                            "then": "sent_via_ai",
                                            "else": "sent_by_human"
                                        }
                                    }
                                }
                            }
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            daily_stats = {}
            async for result in db.messages.aggregate(pipeline):
                date = result["_id"]["date"]
                status = result["_id"]["status"]
                count = result["count"]
                
                if date not in daily_stats:
                    daily_stats[date] = {}
                
                daily_stats[date][status] = count
            
            return {
                "workspace_id": workspace_id,
                "export_count": len(export_logs),
                "last_export": export_logs[0]["export_timestamp"].isoformat() if export_logs else None,
                "daily_message_stats": daily_stats,
                "total_exports_last_week": len(export_logs)
            }
            
        except Exception as e:
            logger.error(f"Failed to get export statistics: {e}")
            return {}
    
    async def manual_export(
        self, 
        workspace_id: str, 
        start_date: datetime, 
        end_date: datetime,
        email: Optional[str] = None
    ) -> str:
        """Generate manual export for specific date range"""
        try:
            db = get_database()
            
            # Get workspace details
            workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
            if not workspace:
                raise ValueError(f"Workspace {workspace_id} not found")
            
            workspace_name = workspace["name"]
            
            # Query messages for date range
            pipeline = [
                {
                    "$lookup": {
                        "from": "chats",
                        "localField": "chat_id",
                        "foreignField": "_id",
                        "as": "chat"
                    }
                },
                {
                    "$unwind": "$chat"
                },
                {
                    "$match": {
                        "chat.workspace_id": ObjectId(workspace_id),
                        "timestamp": {"$gte": start_date, "$lte": end_date}
                    }
                },
                {
                    "$sort": {"timestamp": -1}
                }
            ]
            
            messages = []
            async for message in db.messages.aggregate(pipeline):
                messages.append(message)
            
            if not messages:
                raise ValueError("No messages found for the specified date range")
            
            # Generate Excel file
            excel_file_path = await self._create_excel_file(messages, workspace_name, workspace_id)
            
            # Send email if provided
            if email:
                await self._send_email_with_attachment(email, workspace_name, excel_file_path, len(messages))
                # Cleanup file after sending
                if os.path.exists(excel_file_path):
                    os.remove(excel_file_path)
            
            return excel_file_path
            
        except Exception as e:
            logger.error(f"Failed to generate manual export: {e}")
            raise

# Global instance
excel_export_service = ExcelExportService()