from pathlib import Path
from smtplib import SMTPDataError
from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader
from app.database.models import User
from app.services.security.secure_token.manager import token_manager, TokenType
from app.config import settings
from app.utils.logger import logger
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType


conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_USERNAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME="TODO Systems",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates",
)


class EmailService:

    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir)
            )

        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_USERNAME,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_FROM_NAME="TODO Systems",
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=True,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=self.template_dir,
        )

    async def send_email_change_user_email(self, user: User, host: str):
        """
        Send email change user_email
        """
        try:
            token_cahage_email = await token_manager.create_token(
                token_type=TokenType.RESET_EMAIL,
                data={"sub": user.email},
            )
            template = self.jinja_env.get_template(
                "email_change_template.html"
                )

            body = template.render(
                username=user.username, host=host, token=token_cahage_email
            )

            message = MessageSchema(
                subject="Confirm your email",
                recipients=[user.email],
                body=body,
                subtype=MessageType.html,
            )

            fm = FastMail(conf)
            await fm.send_message(message)

        except SMTPDataError as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Failed to send email due to high",
                    "intensity of connections"
                )
            )

        except ConnectionError as err:
            logger.warning(f"Failed to send password reset email: {str(err)}")

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process request",
            )

    async def send_password_reset_email(self, user: User, host: str):
        """
        Send email reset password
        """
        try:

            toke_change_password = await token_manager.create_token(
                token_type=TokenType.RESET_PASSWORD,
                data={"sub": user.email},
            )

            template = self.jinja_env.get_template(
                "reset_password_template.html"
            )

            body = template.render(
                username=user.username, host=host, token=toke_change_password
            )

            message = MessageSchema(
                subject="Password Reset Request for Your Account",
                recipients=[user.email],
                body=body,
                subtype=MessageType.html,
            )

            fm = FastMail(conf)
            await fm.send_message(message)
            print(f"Password reset email sent successfully to {user.email}")

        except SMTPDataError as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Failed to send email due to high",
                    "intensity of connections"
                )
            )

        except ConnectionError as err:
            logger.warning(f"Failed to send password reset email: {str(err)}")

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process request",
            )


email_service = EmailService()
