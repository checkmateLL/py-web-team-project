from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pathlib import Path

from app.utils.rate_limit import rate_limited
from app.services.security.auth_service import role_deps
from app.routers.routers import api_router
from app.config import settings
from app.database.connection import get_conn_db


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
)
app.include_router(router=api_router)

base_dir = Path(__file__).parent
templates = Jinja2Templates(directory=base_dir / "templates")

app.mount(
    "/static", StaticFiles(directory=base_dir / "templates" / "static"), name="static"
)


@app.get("/")
@rate_limited(max_calls=5, time_frame=1)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/check-connection-db")
async def healthchecker(
    db: AsyncSession = Depends(get_conn_db), current_user=role_deps.admin_only()
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED"
            )
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=500, detail="Database is not configured correctly"
            )
        return {"message": "Database normally works"}
    except Exception:
        raise HTTPException(status_code=500, detail="Error connecting to the database")
