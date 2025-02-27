from fastapi import FastAPI, Depends, HTTPException, status
from fastapi_limiter import FastAPILimiter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager
from fastapi_limiter.depends import RateLimiter

from app.services.security.auth_service import role_deps
from app.routers.routers import api_router
from app.config import settings
from app.database.connection import get_conn_db
from app.services.user_service import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    client_redis = await redis_client.get_redis_client()
    await FastAPILimiter.init(client_redis)
    yield

    await redis_client.close()
    await FastAPILimiter.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)
app.include_router(router=api_router)


@app.get("/")
async def index(
    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, minutes=1))
):
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