from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from .. import scoring

router = APIRouter(prefix="/score", tags=["score"])

_status = {"running": False, "last_result": None}

def _run(db: Session):
    _status["running"] = True
    try:
        _status["last_result"] = scoring.recalculate_all(db)
    finally:
        _status["running"] = False
        db.close()

@router.post("/recalculate")
def recalculate(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if _status["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(_run, db)
    return {"status": "started"}

@router.get("/status")
def score_status():
    return _status
