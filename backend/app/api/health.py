from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncEngine
from app.database import engine

router = APIRouter(prefix="/api/v1/health", tags=["Health"])

@router.get("")
async def health_check():
    return {"status": "ok", "service": "autoclip-backend"}

@router.get("/db")
async def db_health_check():
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}
