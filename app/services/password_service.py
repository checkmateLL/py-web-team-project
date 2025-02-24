from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status
import logging
from typing import Optional

from app.config import settings
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class PasswordResetService:
    """
    Service for handling password reset functionality.
    
    This class handles JWT token creation and verification for password resets.
    """

    def __init__(self, email_service: EmailService):
        """
        Initialize PasswordResetService.
        
        Args:
            email_service (EmailService): Email service for sending password reset emails.
        """
        self.email_service = email_service

    def create_reset_token(self, email: str) -> str:
        """
        Creates a password reset token with 1-hour expiration.
        
        Args:
            email (str): User email to encode in the token.
            
        Returns:
            str: JWT token string.
            
        Raises:
            HTTPException: 500 Internal Server Error if token creation fails.
        """
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
        """
        Verifies a password reset token and returns the email if valid.
        
        Args:
            token (str): JWT token to verify.
            
        Returns:
            str: Email address extracted from valid token.
            
        Raises:
            HTTPException: 
                - 400 Bad Request if token is invalid, expired, or has wrong type.
                - 400 Bad Request if any JWT decoding error occurs.
        """
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