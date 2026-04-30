from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

def get_or_create_tag(db: Session, name: str) -> models.Tag:
    tag = db.query(models.Tag).filter_by(name=name.lower().strip()).first()
    if not tag:
        tag = models.Tag(name=name.lower().strip())
        db.add(tag)
        db.flush()
    return tag

@router.get("/", response_model=list[schemas.ProjectOut])
def list_projects(
    category: str | None = None,
    sort: str = "published",
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    q = db.query(models.Project)
    if category:
        q = q.filter(models.Project.category == category)
    if sort == "score":
        q = q.order_by(models.Project.score.desc(), models.Project.published_at.desc())
    elif sort == "published":
        q = q.order_by(models.Project.published_at.desc().nullslast(), models.Project.created_at.desc())
    else:
        q = q.order_by(models.Project.created_at.desc())
    return q.offset(skip).limit(limit).all()

@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/", response_model=schemas.ProjectOut, status_code=201)
def create_project(data: schemas.ProjectCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Project).filter_by(behance_id=data.behance_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Project already exists")
    project = models.Project(
        behance_id=data.behance_id,
        title=data.title,
        url=data.url,
        cover_url=data.cover_url,
        author_name=data.author_name,
        author_id=data.author_id,
        category=data.category,
        published_at=data.published_at,
        is_manual=data.is_manual,
    )
    for tag_name in data.tags:
        project.tags.append(get_or_create_tag(db, tag_name))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def patch_project(project_id: int, data: schemas.ProjectPatch, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.cover_url is not None:
        project.cover_url = data.cover_url
    if data.category is not None:
        project.category = data.category
    if data.score is not None:
        project.score = data.score
    if data.published_at is not None:
        project.published_at = data.published_at
    if data.awards is not None:
        project.awards = data.awards
    if data.tags is not None:
        project.tags = []
        for tag_name in data.tags:
            tag = db.query(models.Tag).filter_by(name=tag_name.lower().strip()).first()
            if not tag:
                tag = models.Tag(name=tag_name.lower().strip())
                db.add(tag)
                db.flush()
            project.tags.append(tag)
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
