import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from rq.job import Job, NoSuchJobError

from app.core.config import settings
from app.core.queue import redis_conn

router = APIRouter()


@router.get("/{result_id}")
def download_file(result_id: str):
    # Verify result_id is a UUID (prevents basic traversal)
    try:
        uuid.UUID(result_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid result ID format")

    try:
        job = Job.fetch(result_id, connection=redis_conn)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Result not found")

    if job.get_status() != "finished" or not job.result or job.result.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Result not available or failed")

    file_path = job.result.get("output_file")
    if not file_path:
        raise HTTPException(status_code=404, detail="Result not available")

    path = Path(file_path).resolve()
    base_path = Path(settings.TEMP_STORAGE_PATH).resolve()

    # Secure path traversal check
    try:
        path.relative_to(base_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not path.exists() or path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="File missing, expired, or invalid")

    return FileResponse(path, media_type="application/pdf", filename=f"{result_id}.pdf")
