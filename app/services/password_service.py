from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status
import logging
from typing import Optional

from app.config import settings
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    def create_reset_token(self, email: str) -> str:
        """Creates a password reset token."""
        expires = datetime.utcnow() + timedelta(hours=1)
        token_data = {
            "sub": email,
            "type": "password_reset",
            "exp": expires.timestamp()
        }
        
        try:
            token = jwt.encode(
                token_data,
                settings.SECRET_KEY_JWT,
                algorithm=settings.ALGORITHM
            )
            return token
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create reset token"
            )

    def verify_reset_token(self, token: str) -> str:
        """Verifies a password reset token and returns the email if valid."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY_JWT,
                algorithms=[settings.ALGORITHM]
            )
            
            # Verify token type
            if payload.get("type") != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type"
                )

            exp_timestamp = payload.get("exp")
            if not exp_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token missing expiration"
                )
        
            current_timestamp = datetime.utcnow().timestamp()
            if float(exp_timestamp) < current_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token has expired"
                )

            email = payload.get("sub")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token"
                )

            return email

        except JWTError as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )