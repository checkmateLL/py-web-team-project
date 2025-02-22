from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.security.auth_service import role_deps
from app.routers.routers import api_router
from app.config import settings
from app.database.connection import get_conn_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION
)
app.include_router(router=api_router)

@app.get("/")
async def index():
    return {"message": "home page"}

@app.get("/check-connection-db")
async def healthchecker(
    db: AsyncSession = Depends(get_conn_db),
    current_user = role_deps.admin_only()
    ):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='UNAUTHORIZED'
            )
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=500,
                detail="Database is not configured correctly"
            )
        return {
            "message": 
            "Database normally works"
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error connecting to the database"
        )