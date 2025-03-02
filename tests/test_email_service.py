import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.services.email_service import EmailService
from app.database.models import User


@pytest.fixture
def mock_fastmail():
    with patch("app.services.email_service.FastMail") as mock:
        mock_instance = MagicMock()
        mock_instance.send_message = AsyncMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.email = "test@example.com"
    user.username = "testuser"
    return user


@pytest.mark.asyncio
async def test_send_email_change_user_email(mock_fastmail, mock_user):
    # Given
    email_service = EmailService()
    host = "http://testhost/"
    
    # When
    with patch("app.services.email_service.token_manager.create_token", 
              return_value="mock-token"):
        await email_service.send_email_change_user_email(mock_user, host)
    
    # Then
    mock_fastmail.assert_called_once()
    mock_fastmail.return_value.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_password_reset_email(mock_fastmail, mock_user):
    # Given
    email_service = EmailService()
    host = "http://testhost/"
    
    # When
    with patch("app.services.email_service.token_manager.create_token", 
              return_value="mock-token"):
        await email_service.send_password_reset_email(mock_user, host)
    
    # Then
    mock_fastmail.assert_called_once()
    mock_fastmail.return_value.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_email_error_handling(mock_user):
    # Given
    email_service = EmailService()
    host = "http://testhost/"
    
    # When/Then
    with patch("app.services.email_service.FastMail", 
              side_effect=Exception("Connection error")):
        with pytest.raises(HTTPException) as exc_info:
            await email_service.send_password_reset_email(mock_user, host)
        assert exc_info.value.status_code == 500