# email_service.py

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from pydantic import EmailStr

from app.config import settings

class EmailService:
    async def send_email(self, recipient: EmailStr, subject: str, body: str):
        """Send an email"""
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            async with aiosmtplib.SMTP(
                hostname=settings.MAIL_SERVER,
                port=settings.MAIL_PORT,
                use_tls=settings.MAIL_SSL_TLS,
                start_tls=settings.MAIL_STARTTLS
            ) as smtp:
                await smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                await smtp.send_message(msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    async def send_password_reset_email(self, recipient: EmailStr, reset_token: str):
        """Send password reset link"""
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        body = f"""
        <p>Hello,</p>
        <p>You have requested to reset your password. Click the link below to proceed:</p>
        <p><a href="{reset_link}">Reset Password</a></p>
        <p>This link will expire in {settings.RESET_TOKEN_EXPIRE_HOURS} hour(s).</p>
        <p>If you didn't request this, please ignore this email.</p>
        """
        await self.send_email(recipient, "Reset Your Password", body)

    async def send_password_changed_email(self, recipient: EmailStr):
        """Send password change notification"""
        body = """
        <p>Hello,</p>
        <p>Your password has been successfully changed.</p>
        <p>If you didn't make this change, please contact support immediately.</p>
        """
        await self.send_email(recipient, "Password Changed Successfully", body)