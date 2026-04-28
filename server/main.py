from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from .routers import projects, likes, follows, sync, score

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Behance Curator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(likes.router)
app.include_router(follows.router)
app.include_router(sync.router)
app.include_router(score.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "Behance Curator API"}

@app.get("/health")
def health():
    return {"status": "ok"}
