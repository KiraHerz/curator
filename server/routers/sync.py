from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from .. import rss

router = APIRouter(prefix="/sync", tags=["sync"])

_sync_status = {"running": False, "last_result": None}

def _run_sync(db: Session):
    _sync_status["running"] = True
    try:
        result = rss.sync_all(db)
        total = sum(result.values())
        _sync_status["last_result"] = {
            "total_added": total,
            "by_designer": result
        }
    finally:
        _sync_status["running"] = False
        db.close()

@router.post("/")
def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if _sync_status["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(_run_sync, db)
    return {"status": "started"}

@router.get("/status")
def sync_status():
    return _sync_status
