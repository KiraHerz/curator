from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, scoring
from ..database import get_db

router = APIRouter(prefix="/likes", tags=["likes"])

@router.get("/", response_model=list[schemas.LikeOut])
def list_likes(db: Session = Depends(get_db)):
    return db.query(models.Like).order_by(models.Like.liked_at.desc()).all()

@router.post("/", response_model=schemas.LikeOut, status_code=201)
def add_like(data: schemas.LikeCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(models.Like).filter_by(project_id=data.project_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already liked")
    like = models.Like(project_id=data.project_id, source=data.source)
    db.add(like)
    db.commit()
    db.refresh(like)
    scoring.recalculate_one(db, data.project_id)
    return like

@router.delete("/{project_id}", status_code=204)
def remove_like(project_id: int, db: Session = Depends(get_db)):
    like = db.query(models.Like).filter_by(project_id=project_id).first()
    if not like:
        raise HTTPException(status_code=404, detail="Like not found")
    db.delete(like)
    db.commit()
    scoring.recalculate_all(db)
