from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


from app.database.connection import get_conn_db

app = FastAPI()


@app.get("/")
async def index():
    return {"message": "home page"}

@app.get("/check-connection-db")
async def healthchecker(db: AsyncSession = Depends(get_conn_db)):
    try:
        
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