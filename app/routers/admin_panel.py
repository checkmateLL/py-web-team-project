from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services.security.auth_service import role_deps
from app.repository.users import crud_users
from app.database.connection import get_conn_db

router = APIRouter(prefix='/admin_panel')

@router.put(
        '/ban-user/{user_id}',
        status_code=status.HTTP_200_OK,
        responses={
        200: {
            "description": "User is already deactivated",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User is already deactivated",
                        "user": {
                            "id": 1,
                            "username": "john_doe",
                            "is_active": False
                        }
                    }
                }
            }
        },
        204: {
            "description": "User successfully deactivated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "is_active": False
                    }
                }
            }
        },
        404: {"description": "User not found"},
        500: {"description": "Database error occurred"},
        403: {"description": "Forbidden. Only admin can perform this action"}
    }
)
async def desactivate_user(
    user_id:int = Path(..., description='ID of the user to deactivate', gt=0),
    session : AsyncSession = Depends(get_conn_db),
    _ : User = role_deps.admin_only()
):
    """
    Deactivate a user by settings 'is_active' to False

    - **user_id**: ID if the user to deactivate
    - **Requires admin previleges**:
    """
    result = await crud_users.desactivate_user(user_id, session)
    if isinstance (result, dict):
        return result
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.put(
        '/unban-user/{user_id}',
        status_code=status.HTTP_200_OK,
        responses={
        200: {
            "description": "User is already activated",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User is already activated",
                        "user": {
                            "id": 1,
                            "username": "john_doe",
                            "is_active": True
                        }
                    }
                }
            }
        },
        204: {
            "description": "User successfully activated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "is_active": True
                    }
                }
            }
        },
        404: {"description": "User not found"},
        500: {"description": "Database error occurred"},
        403: {"description": "Forbidden. Only admin can perform this action"}
    }
)
async def activate_user(
    user_id:int = Path(..., description='ID of the user to activate', gt=0),
    session : AsyncSession = Depends(get_conn_db),
    _ : User = role_deps.admin_only()
):
    """
    Aactivate a user by settings 'is_active' to True

    - **user_id**: ID if the user to Activate
    - **Requires admin previleges**:
    """
    result = await crud_users.activate_user(user_id, session)
    if isinstance (result, dict):
        return result
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
