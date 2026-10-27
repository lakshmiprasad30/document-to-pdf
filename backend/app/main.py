import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.files import router as files_router
from app.api.endpoints.jobs import router as jobs_router
from app.api.health import router as health_router
from app.core.config import settings
from app.worker.cleanup import cleanup_task

# Centralized logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start cleanup background task
    task = asyncio.create_task(cleanup_task())
    yield
    # Shutdown: Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Document to PDF API", lifespan=lifespan)

origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(health_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(files_router, prefix="/api/v1/files", tags=["files"])


@app.get("/")
def read_root():
    return {"message": "Welcome to Document to PDF API"}
