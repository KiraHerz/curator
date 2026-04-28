from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/follows", tags=["follows"])

@router.get("/", response_model=list[schemas.FollowOut])
def list_follows(level: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Follow)
    if level:
        q = q.filter(models.Follow.level == level)
    return q.order_by(models.Follow.added_at.desc()).all()

@router.post("/", response_model=schemas.FollowOut, status_code=201)
def add_follow(data: schemas.FollowCreate, db: Session = Depends(get_db)):
    if data.level not in (1, 2):
        raise HTTPException(status_code=400, detail="Level must be 1 or 2")
    existing = db.query(models.Follow).filter_by(
        designer_id=data.designer_id, level=data.level
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Follow already exists")
    follow = models.Follow(
        designer_id=data.designer_id,
        name=data.name,
        level=data.level,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)
    return follow

@router.delete("/{designer_id}", status_code=204)
def remove_follow(designer_id: str, db: Session = Depends(get_db)):
    follows = db.query(models.Follow).filter_by(designer_id=designer_id).all()
    if not follows:
        raise HTTPException(status_code=404, detail="Follow not found")
    for f in follows:
        db.delete(f)
    db.commit()
