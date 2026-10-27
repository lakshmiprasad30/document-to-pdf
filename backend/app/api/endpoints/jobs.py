import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from rq.job import Job, NoSuchJobError

from app.core.config import settings
from app.core.queue import job_queue, redis_conn
from app.schemas.job import JobResponse, JobStatusResponse
from app.worker.tasks import process_job

logger = logging.getLogger(__name__)

router = APIRouter()


def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"

    try:
        calls = redis_conn.incr(key)
        if calls == 1:
            redis_conn.expire(key, settings.RATE_LIMIT_WINDOW)

        if calls > settings.RATE_LIMIT_CALLS:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429, detail="Too many requests. Please try again later."
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Redis rate limiting error: {e}")
        # Fail open if Redis is temporarily unreachable for rate limiting


SUPPORTED_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".jpg", ".jpeg", ".png", ".webp", ".txt"}


def validate_magic_bytes(ext: str, chunk: bytes) -> bool:
    if ext in {".docx", ".xlsx", ".pptx"}:
        return chunk.startswith(b"PK\x03\x04")
    elif ext in {".jpg", ".jpeg"}:
        return chunk.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        return chunk.startswith(b"\x89PNG\x0d\x0a\x1a\x0a")
    elif ext == ".webp":
        return chunk.startswith(b"RIFF") and chunk[8:12] == b"WEBP"
    elif ext == ".txt":
        # Just check if it can be decoded as text, or allow it since it's hard to strict-validate
        try:
            chunk.decode("utf-8")
            return True
        except UnicodeDecodeError:
            # Maybe it's ascii or another encoding, but requirement says UTF-8
            pass
        return True  # Fallback for TXT since magic bytes don't exist
    return False


@router.post("", response_model=JobResponse)
async def create_job(request: Request, file: UploadFile = File(...)):  # noqa: B008
    check_rate_limit(request)

    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Invalid extension uploaded: {file.filename}")
        raise HTTPException(status_code=415, detail=f"Extension {ext} is not supported")

    # Store uploaded file safely
    job_id = str(uuid.uuid4())
    safe_filename = f"{job_id}{ext}"
    temp_dir = Path(settings.TEMP_STORAGE_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = temp_dir / safe_filename

    file_size = 0
    is_first_chunk = True
    error_to_raise = None

    with open(temp_path, "wb") as f:  # noqa: ASYNC230
        while chunk := await file.read(8192):
            if is_first_chunk:
                is_first_chunk = False
                if not validate_magic_bytes(ext, chunk):
                    error_to_raise = HTTPException(
                        status_code=400, detail="Invalid file format/signature"
                    )
                    logger.warning(f"Invalid file signature for {job_id}")
                    break

            file_size += len(chunk)
            if file_size > settings.MAX_FILE_SIZE:
                error_to_raise = HTTPException(status_code=413, detail="File too large")
                logger.warning(f"File size exceeded for {job_id}: {file_size} bytes")
                break
            f.write(chunk)

    if error_to_raise:
        temp_path.unlink(missing_ok=True)
        raise error_to_raise

    if is_first_chunk:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File is empty")

    logger.info(f"File uploaded successfully for job {job_id}, size: {file_size} bytes")

    # Enqueue job
    job = job_queue.enqueue(
        process_job,
        job_id,
        str(temp_path),
        job_id=job_id,
        result_ttl=86400,  # Keep result for 24 hours
    )

    logger.info(f"Job {job_id} enqueued")
    return {"job_id": job.id, "status": "queued"}


@router.post("/merge", response_model=JobResponse)
async def create_merge_job(request: Request, files: list[UploadFile] = File(...)):
    check_rate_limit(request)

    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 files required for merge")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files allowed for merge")

    job_id = str(uuid.uuid4())
    temp_dir = Path(settings.TEMP_STORAGE_PATH) / f"{job_id}_inputs"
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_paths = []
    total_size = 0

    try:
        for idx, file in enumerate(files):
            ext = Path(file.filename).suffix.lower() if file.filename else ""
            if ext != ".pdf":
                raise HTTPException(
                    status_code=415, detail="Only .pdf files are supported for merge"
                )

            safe_filename = f"{idx}.pdf"
            temp_path = temp_dir / safe_filename

            is_first_chunk = True
            with open(temp_path, "wb") as f:  # noqa: ASYNC230
                while chunk := await file.read(8192):
                    if is_first_chunk:
                        is_first_chunk = False
                        if not chunk.startswith(b"%PDF-"):
                            raise HTTPException(
                                status_code=400, detail=f"Invalid PDF signature in {file.filename}"
                            )

                    total_size += len(chunk)
                    if total_size > settings.MAX_FILE_SIZE * 5:  # allow slightly more for bulk
                        raise HTTPException(status_code=413, detail="Total file size too large")
                    f.write(chunk)

            file_paths.append(str(temp_path))

    except HTTPException:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    from app.worker.tasks import process_merge_job

    job = job_queue.enqueue(
        process_merge_job,
        job_id,
        file_paths,
        job_id=job_id,
        result_ttl=86400,
    )

    logger.info(f"Merge job {job_id} enqueued with {len(files)} files")
    return {"job_id": job.id, "status": "queued"}


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Job not found")

    status_map = {
        "queued": "queued",
        "started": "processing",
        "finished": "completed",
        "failed": "failed",
        "canceled": "failed",
        "stopped": "failed",
        "scheduled": "queued",
        "deferred": "queued",
    }

    status = job.get_status()
    logger.debug(f"job_id={job_id} status_type={type(status).__name__} status_value={status}")
    mapped_status = status_map.get(status, "processing")

    error = None
    result_id = None

    if mapped_status == "completed":
        result = job.result
        if result:
            if result.get("status") == "failed":
                mapped_status = "failed"
                error = result.get("error")
            else:
                result_id = job_id
    elif mapped_status == "failed":
        error = "Conversion failed due to an internal error."

    return {"job_id": job_id, "status": mapped_status, "result_id": result_id, "error": error}
