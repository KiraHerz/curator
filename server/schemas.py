from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- Tag ---
class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}

# --- Project ---
class ProjectCreate(BaseModel):
    behance_id: str
    title: str
    url: str
    cover_url: Optional[str] = None
    author_name: str
    author_id: str
    category: str
    tags: list[str] = []
    published_at: Optional[datetime] = None
    awards: Optional[str] = None
    is_manual: bool = False

class ProjectOut(BaseModel):
    id: int
    behance_id: str
    title: str
    url: str
    cover_url: Optional[str]
    author_name: str
    author_id: str
    category: str
    score: float
    is_manual: bool
    awards: Optional[str] = None
    slides: Optional[str] = None
    published_at: Optional[datetime]
    created_at: datetime
    tags: list[TagOut] = []
    model_config = {"from_attributes": True}

# --- Like ---
class LikeCreate(BaseModel):
    project_id: int
    source: str = "manual"  # "behance" or "manual"

class LikeOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    source: str
    liked_at: datetime
    model_config = {"from_attributes": True}

# --- Follow ---
class FollowCreate(BaseModel):
    designer_id: str
    name: str
    level: int  # 1 or 2

class FollowOut(BaseModel):
    id: int
    designer_id: str
    name: str
    level: int
    added_at: datetime
    model_config = {"from_attributes": True}

class ProjectPatch(BaseModel):
    cover_url: Optional[str] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None
    score: Optional[float] = None
    published_at: Optional[datetime] = None
    awards: Optional[str] = None
