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
from bson import ObjectId
import logging
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ExcelReportService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.report_dir = "reports"
        os.makedirs(self.report_dir, exist_ok=True)
    
    async def generate_workspace_reports(self):
        """Generate Excel reports for all workspaces with recent activity"""
        try:
            logger.info("Starting automated Excel report generation")
            
            db = get_database()
            
            # Get all active workspaces
            workspaces = await db.workspaces.find({"status": "active"}).to_list(None)
            
            if not workspaces:
                logger.info("No active workspaces found")
                return
            
            # Process each workspace
            for workspace in workspaces:
                try:
                    await self._generate_workspace_report(workspace)
                except Exception as e:
                    logger.error(f"Failed to generate report for workspace {workspace['_id']}: {e}")
                    continue
            
            logger.info("Completed automated Excel report generation")
            
        except Exception as e:
            logger.error(f"Excel report generation failed: {e}")
    
    async def _generate_workspace_report(self, workspace: Dict[str, Any]):
        """Generate and send Excel report for a specific workspace"""
        workspace_id = str(workspace["_id"])
        workspace_name = workspace["name"]
        
        try:
            logger.info(f"Generating report for workspace: {workspace_name} ({workspace_id})")
            
            # Get workspace email configuration
            email_key = f"WORKSPACE_{workspace_id}_EMAIL"
            workspace_email = os.getenv(email_key)
            
            if not workspace_email:
                logger.warning(f"No email configured for workspace {workspace_id} (key: {email_key})")
                return
            
            # Get messages from last 15 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=15)
            
            # Query messages for this workspace
            db = get_database()
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
                        "timestamp": {"$gte": cutoff_time}
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
                logger.info(f"No recent messages for workspace {workspace_name}")
                return
            
            logger.info(f"Found {len(messages)} messages for workspace {workspace_name}")
            
            # Generate Excel file
            excel_file_path = await self._create_excel_file(messages, workspace_name, workspace_id)
            
            # Send email
            await self._send_email_report(
                workspace_email,
                workspace_name,
                excel_file_path,
                len(messages)
            )
            
            # Cleanup file
            if os.path.exists(excel_file_path):
                os.remove(excel_file_path)
            
            logger.info(f"Report sent successfully for workspace {workspace_name}")
            
        except Exception as e:
            logger.error(f"Failed to generate report for workspace {workspace_name}: {e}")
            raise
    
    async def _create_excel_file(
        self, 
        messages: List[Dict[str, Any]], 
        workspace_name: str,
        workspace_id: str
    ) -> str:
        """Create Excel file from messages data"""
        try:
            # Prepare data for Excel
            excel_data = []
            
            for message in messages:
                chat = message.get("chat", {})
                
                # Determine sender and receiver
                if message.get("direction") == "incoming":
                    sender_phone = chat.get("customer_phone", "Unknown")
                    receiver_phone = chat.get("phone_number", "Unknown")
                    status = "Received"
                else:
                    sender_phone = chat.get("phone_number", "Unknown")
                    receiver_phone = chat.get("customer_phone", "Unknown")
                    status = "AI Generated" if message.get("is_ai_generated") else "Human Sent"
                
                excel_data.append({
                    "Sender Phone Number": sender_phone,
                    "Receiver Phone Number": receiver_phone,
                    "Message Content": message.get("content", ""),
                    "Timestamp": message.get("timestamp", datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": status,
                    "Message Type": message.get("message_type", "text").title(),
                    "Workspace ID": workspace_id,
                    "Workspace Name": workspace_name,
                    "Chat ID": str(message.get("chat_id", "")),
                    "Customer Name": chat.get("customer_name", ""),
                    "Direction": message.get("direction", "").title()
                })
            
            # Create DataFrame
            df = pd.DataFrame(excel_data)
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
            safe_workspace_name = "".join(c for c in workspace_name if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = f"{safe_workspace_name}_whatsapp_messages_{timestamp}.xlsx"
            file_path = os.path.join(self.report_dir, filename)
            
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
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Add header formatting
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
    
    async def _send_email_report(
        self, 
        recipient_email: str, 
        workspace_name: str, 
        excel_file_path: str,
        message_count: int
    ):
        """Send Excel report via email"""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_username
            msg['To'] = recipient_email
            msg['Subject'] = f"WhatsApp Messages Report - {workspace_name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            
            # Email body
            body = f"""
Dear Team,

Please find attached the WhatsApp messages report for workspace "{workspace_name}".

Report Details:
- Workspace: {workspace_name}
- Time Period: Last 15 minutes
- Total Messages: {message_count}
- Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

This report includes all WhatsApp conversations, AI-generated responses, and customer interactions for the specified time period.

Best regards,
WhatsApp AI Automation System
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach Excel file
            with open(excel_file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(excel_file_path)}'
                )
                msg.attach(part)
            
            # Send email
            await self._send_smtp_email(msg, recipient_email)
            
            logger.info(f"Report email sent to {recipient_email} for workspace {workspace_name}")
            
        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
            raise
    
    async def _send_smtp_email(self, msg: MIMEMultipart, recipient_email: str):
        """Send email using SMTP"""
        def send_email():
            try:
                server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
                server.quit()
                return True
            except Exception as e:
                logger.error(f"SMTP error: {e}")
                raise
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, send_email)
    
    async def generate_manual_report(
        self, 
        workspace_id: str, 
        start_date: datetime, 
        end_date: datetime,
        email: Optional[str] = None
    ) -> str:
        """Generate manual report for specific date range"""
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
                await self._send_email_report(email, workspace_name, excel_file_path, len(messages))
            
            return excel_file_path
            
        except Exception as e:
            logger.error(f"Failed to generate manual report: {e}")
            raise
    
    async def get_report_history(self, workspace_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of generated reports for a workspace"""
        try:
            db = get_database()
            
            # This would require a reports collection to track generated reports
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get report history: {e}")
            return []

# Global instance
excel_report_service = ExcelReportService()