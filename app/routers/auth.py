from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.users import crud_users
from app.services.security.secure_token.manager import TokenType, token_manager
from app.services.security.secure_password import Hasher
from app.services.security.auth_service import AuthService
from app.database.connection import get_conn_db
from app.config import settings
import app.schemas as sch
from app.utils.rate_limit import rate_limited

router = APIRouter(prefix='/auth')

@router.post(
          "/register", 
          status_code=200, 
          response_model=sch.ResponseUser
    )
@rate_limited(
     max_calls=settings.RL_TIMES_AUTH, 
     time_frame=settings.RL_MINUTES_AUTH
    )
async def register_user(
    request: Request,
    body : sch.RegisterUser,
    session: AsyncSession = Depends(get_conn_db),
):
    """
    Register a new user with validated username and password.
    
    Username requirements:
    - 3-50 characters
    - Only letters, numbers, underscores, and hyphens
    
    Password requirements:
    - At least 6 characters
    - Contains at least one digit
    - Contains at least one uppercase letter
    """
    
    if await crud_users.exist_user(
        body.email, 
        session
    ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User already register'
            )

    password = Hasher.get_password_hash(body.password)
    new_user = await crud_users.create_new_user(
        email=body.email, 
        user_name=body.user_name, 
        password=password, 
        session=session
        )
    return sch.ResponseUser.from_orm(new_user)

@router.post("/login", response_model=sch.ResponseLogin)
@rate_limited(max_calls=settings.RL_TIMES_AUTH, time_frame=settings.RL_MINUTES_AUTH)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  
    db: AsyncSession= Depends(get_conn_db),
):
    """
    login user in system
    """
    user = await crud_users.autenticate_user(
         form_data.username, 
         form_data.password,
         db
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if user.is_active == False:
         raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail='You dont have access'
         )

    encode_access_token = await token_manager.create_token(
        token_type=TokenType.ACCESS,
        data={'sub': user.email},
    )
    encode_refresh_token = await token_manager.create_token(
        token_type=TokenType.REFRESH,
        data={'sub': user.email},
    )

    return {
        "access_token": encode_access_token, 
        "refresh_token": encode_refresh_token,
        "token_type": "bearer"}

@router.post("/logout")
async def logout(
    result: dict = Depends(AuthService().logout_set)
):
    """
    Logout the current user by blacklist their access token.

    Returns:
        dict: A access message confirming logout.
    """
    return result