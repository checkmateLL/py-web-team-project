# email_service.py
import logging
from pathlib import Path
from typing import Dict, Optional
from fastapi import HTTPException
from pydantic import EmailStr
from jinja2 import Environment, FileSystemLoader
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.conf = {
            "MAIL_USERNAME": settings.MAIL_USERNAME,
            "MAIL_PASSWORD": settings.MAIL_PASSWORD,
            "MAIL_FROM": settings.MAIL_FROM,
            "MAIL_PORT": settings.MAIL_PORT,
            "MAIL_SERVER": settings.MAIL_SERVER,
            "MAIL_FROM_NAME": settings.MAIL_FROM_NAME,
            "MAIL_STARTTLS": settings.MAIL_STARTTLS,
            "MAIL_SSL_TLS": settings.MAIL_SSL_TLS,
        }
        
        # Update template directory to your actual location
        template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

    async def send_password_reset_email(self, email: EmailStr, token: str) -> bool:
        """Send password reset email"""
        try:
            return await self.send_email(
                recipient=email,
                subject="Password Reset Request - PhotoShare",
                template_name="reset_password_template.html",  # Updated to your actual template name
                template_body={
                    "token": token,
                }
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to send password reset email"
            )

    async def send_password_changed_email(self, email: EmailStr) -> bool:
        """Send password changed confirmation email"""
        try:
            return await self.send_email(
                recipient=email,
                subject="Password Changed - PhotoShare",
                template_name="email_template.html",  # Using your general email template
                template_body={
                    "subject": "Password Changed Successfully",
                    "message": "Your password has been successfully changed. If you did not make this change, please contact support immediately."
                }
            )
        except Exception as e:
            logger.error(f"Failed to send password changed email: {str(e)}")
            return False

    async def send_email(
        self, 
        recipient: EmailStr, 
        subject: str,
        template_name: str,
        template_body: dict
    ) -> bool:
        """Send an email using template."""
        try:
            template = self.jinja_env.get_template(template_name)
            body = template.render(**template_body)

            message = MIMEMultipart()
            message['From'] = f"{self.conf['MAIL_FROM_NAME']} <{self.conf['MAIL_FROM']}>"
            message['To'] = recipient
            message['Subject'] = subject
            message.attach(MIMEText(body, 'html'))

            async with aiosmtplib.SMTP(
                hostname=self.conf['MAIL_SERVER'], 
                port=self.conf['MAIL_PORT'],
                use_tls=self.conf['MAIL_SSL_TLS']
            ) as smtp:
                await smtp.login(self.conf['MAIL_USERNAME'], self.conf['MAIL_PASSWORD'])
                await smtp.send_message(message)

            logger.info(f"Email sent successfully to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to send email: {str(e)}"
            )

email_service = EmailService()