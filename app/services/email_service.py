# email_service.py
import logging
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
        # Extract secret values if they are SecretStr
        mail_username = (
            settings.mail_username.get_secret_value() 
            if hasattr(settings.mail_username, 'get_secret_value') 
            else settings.mail_username
        )
        mail_password = (
            settings.mail_password.get_secret_value() 
            if hasattr(settings.mail_password, 'get_secret_value') 
            else settings.mail_password
        )

        self.conf = {
            "MAIL_USERNAME": mail_username,
            "MAIL_PASSWORD": mail_password,
            "MAIL_FROM": settings.mail_from,
            "MAIL_PORT": settings.mail_port,
            "MAIL_SERVER": settings.mail_server,
            "MAIL_FROM_NAME": settings.mail_from_name,
            "MAIL_STARTTLS": settings.mail_starttls,
            "MAIL_SSL_TLS": settings.mail_ssl_tls,
        }
        
        self.logger = logging.getLogger(__name__)
        self.jinja_env = Environment(
            loader=FileSystemLoader('src/services/templates'),
            autoescape=True
        )

    async def send_email(
        self, 
        recipient: EmailStr, 
        subject: str,
        template_name: str,
        template_body: Dict
    ) -> bool:
        """
        Send an email using template.
        """
        try:
            # Render the template
            template = self.jinja_env.get_template(template_name)
            body = template.render(**template_body)

            # Create a multipart message
            message = MIMEMultipart()
            message['From'] = f"{self.conf['MAIL_FROM_NAME']} <{self.conf['MAIL_FROM']}>"
            message['To'] = recipient
            message['Subject'] = subject

            # Attach the HTML body
            message.attach(MIMEText(body, 'html'))

            # Send email using aiosmtplib
            async with aiosmtplib.SMTP(
                hostname=self.conf['MAIL_SERVER'], 
                port=self.conf['MAIL_PORT'],
                use_tls=self.conf['MAIL_SSL_TLS']
            ) as smtp:
                await smtp.login(self.conf['MAIL_USERNAME'], self.conf['MAIL_PASSWORD'])
                await smtp.send_message(message)

            self.logger.info(f"Email sent successfully to {recipient}")
            return True

        except Exception as e:
            self.logger.error(f"Email sending failed: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to send email: {str(e)}"
            )

    async def send_password_reset_email(
        self, 
        email: EmailStr, 
        token: str
    ) -> bool:
        """
        Send password reset email
        """
        try:
            return await self.send_email(
                recipient=email,
                subject="Password Reset Request",
                template_name="password_reset.html",
                template_body={
                    "token": token,
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to send password reset email: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

email_service = EmailService()