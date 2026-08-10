from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router as academic_setup_router
from app.database import Base, engine
import app.models  # noqa: F401 - imports model metadata before create_all
from app.storage import uploads_directory


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="RubriCheck AI API",
    version="0.2.0",
    description="Human-in-the-loop handwritten exam evaluation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(academic_setup_router)
app.mount("/uploads", StaticFiles(directory=uploads_directory), name="uploads")


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "rubricheck-ai-api"}
