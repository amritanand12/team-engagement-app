from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_active_db_info, get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    db_info = get_active_db_info()
    return {
        "status": "ok",
        "database": db_info["dialect"],
        "is_fallback": db_info["is_fallback"],
    }
