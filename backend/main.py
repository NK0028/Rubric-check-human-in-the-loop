from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth_router, router as academic_setup_router
from app.database import Base, engine, migrate_legacy_schema
from app.config import allowed_hosts, cors_origins, environment
import app.models  # noqa: F401 - imports model metadata before create_all
from app.ocr import tesseract_available


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_legacy_schema()
    yield


app = FastAPI(
    title="RubriCheck AI API",
    version="0.2.0",
    description="Human-in-the-loop handwritten exam evaluation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.include_router(academic_setup_router)
app.include_router(auth_router)


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "rubricheck-ai-api", "environment": environment, "ocr": "available" if tesseract_available() else "unavailable"}
