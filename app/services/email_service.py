import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from app.config import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def send_email_with_attachment(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        attachment_name: Optional[str] = None
    ) -> bool:
        """Send email with optional attachment"""
        try:
            # Validate SMTP configuration
            if not all([settings.smtp_server, settings.smtp_username, settings.smtp_password]):
                raise ValueError("SMTP configuration incomplete")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_username
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachment if provided
            if attachment_path and attachment_name:
                await self._add_attachment(msg, attachment_path, attachment_name)
            
            # Send email in thread pool
            await self._send_smtp_email(msg)
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, file_path: str, filename: str):
        """Add file attachment to email"""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
            raise
    
    async def _send_smtp_email(self, msg: MIMEMultipart):
        """Send email using SMTP in thread pool"""
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
    
    async def test_smtp_connection(self) -> bool:
        """Test SMTP connection and authentication"""
        try:
            def test_connection():
                server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.quit()
                return True
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, test_connection)
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    async def send_export_notification(
        self,
        recipient_email: str,
        workspace_name: str,
        message_count: int,
        export_timestamp: str
    ) -> bool:
        """Send notification email about successful export"""
        try:
            subject = f"WhatsApp Export Notification - {workspace_name}"
            
            body = f"""
Dear Team,

Your WhatsApp messages export has been completed successfully.

Export Details:
- Workspace: {workspace_name}
- Messages Exported: {message_count}
- Export Time: {export_timestamp}
- Status: Completed Successfully

The Excel file has been generated and should be delivered to your configured email address shortly.

Best regards,
WhatsApp AI Automation System
            """.strip()
            
            return await self.send_email_with_attachment(
                recipient_email=recipient_email,
                subject=subject,
                body=body
            )
            
        except Exception as e:
            logger.error(f"Failed to send export notification: {e}")
            return False

# Global email service instance
email_service = EmailService()