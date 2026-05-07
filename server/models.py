from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

project_tags = Table("project_tags", Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id")),
    Column("tag_id", Integer, ForeignKey("tags.id"))
)

class Project(Base):
    __tablename__ = "projects"
    id           = Column(Integer, primary_key=True)
    behance_id   = Column(String, unique=True, index=True)
    title        = Column(String)
    url          = Column(String)
    cover_url    = Column(String)
    author_name  = Column(String)
    author_id    = Column(String)
    category     = Column(String)
    score        = Column(Float, default=0)
    is_manual    = Column(Boolean, default=False)
    awards       = Column(String, nullable=True)  # "featured", "adobe_award", "appreciated" or None
    slides       = Column(String, nullable=True)  # JSON array of slide URLs
    published_at = Column(DateTime)
    created_at   = Column(DateTime, default=datetime.utcnow)
    tags         = relationship("Tag", secondary=project_tags, back_populates="projects")
    likes        = relationship("Like", back_populates="project")

class Tag(Base):
    __tablename__ = "tags"
    id       = Column(Integer, primary_key=True)
    name     = Column(String, unique=True, index=True)
    projects = relationship("Project", secondary=project_tags, back_populates="tags")

class Like(Base):
    __tablename__ = "likes"
    id         = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    source     = Column(String)  # "behance" or "manual"
    liked_at   = Column(DateTime, default=datetime.utcnow)
    project    = relationship("Project", back_populates="likes")

class Follow(Base):
    __tablename__ = "follows"
    id          = Column(Integer, primary_key=True)
    designer_id = Column(String, index=True)
    name        = Column(String)
    level       = Column(Integer)  # 1 or 2
    added_at    = Column(DateTime, default=datetime.utcnow)
