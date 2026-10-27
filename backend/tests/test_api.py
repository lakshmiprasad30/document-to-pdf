import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_job_queue():
    with patch("app.api.endpoints.jobs.job_queue") as mock_queue:
        yield mock_queue


@pytest.fixture
def mock_job_fetch():
    with patch("rq.job.Job.fetch") as mock_fetch:
        yield mock_fetch


def test_upload_valid_docx(mock_job_queue):
    fake_job = MagicMock()
    fake_job.id = str(uuid.uuid4())
    mock_job_queue.enqueue.return_value = fake_job

    file_content = b"PK\x03\x04fake docx content"
    files = {
        "file": (
            "test.docx",
            file_content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    response = client.post("/api/v1/jobs", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

    # Verify file was written
    mock_job_queue.enqueue.assert_called_once()
    args = mock_job_queue.enqueue.call_args[0]
    filepath = args[2]
    assert Path(filepath).exists()


def test_upload_invalid_extension(mock_job_queue):
    files = {"file": ("test.exe", b"hello", "application/x-msdownload")}
    response = client.post("/api/v1/jobs", files=files)
    assert response.status_code == 415
    assert "supported" in response.json()["detail"]


def test_get_job_status_queued(mock_job_fetch):
    job_id = str(uuid.uuid4())
    fake_job = MagicMock()
    fake_job.get_status.return_value = "queued"

    mock_job_fetch.return_value = fake_job

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert data["result_id"] is None
    assert data["error"] is None


def test_get_job_status_completed(mock_job_fetch):
    job_id = str(uuid.uuid4())
    fake_job = MagicMock()
    fake_job.get_status.return_value = "finished"
    fake_job.result = {"status": "completed", "output_file": "/tmp/out.pdf"}

    mock_job_fetch.return_value = fake_job

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result_id"] == job_id
    assert data["error"] is None


def test_get_job_status_failed(mock_job_fetch):
    job_id = str(uuid.uuid4())
    fake_job = MagicMock()
    fake_job.get_status.return_value = "finished"
    fake_job.result = {"status": "failed", "error": "Bad DOCX"}

    mock_job_fetch.return_value = fake_job

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error"] == "Bad DOCX"


def test_download_file_valid(mock_job_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TEMP_STORAGE_PATH", str(tmp_path))

    job_id = str(uuid.uuid4())
    fake_job = MagicMock()
    fake_job.get_status.return_value = "finished"

    # Create fake pdf
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n...")

    fake_job.result = {"status": "completed", "output_file": str(pdf_path)}
    mock_job_fetch.return_value = fake_job

    response = client.get(f"/api/v1/files/{job_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4\n..."


def test_download_file_path_traversal(mock_job_fetch):
    # UUID validation should block it immediately
    response = client.get("/api/v1/files/invalid-uuid-string")
    assert response.status_code == 400
    assert "Invalid result ID" in response.json()["detail"]


def test_download_file_traversal_in_redis(mock_job_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TEMP_STORAGE_PATH", str(tmp_path))

    job_id = str(uuid.uuid4())
    fake_job = MagicMock()
    fake_job.get_status.return_value = "finished"

    # Suppose an attacker manipulated Redis to point outside TEMP_STORAGE_PATH
    fake_job.result = {"status": "completed", "output_file": "/etc/passwd"}
    mock_job_fetch.return_value = fake_job

    response = client.get(f"/api/v1/files/{job_id}")
    assert response.status_code == 400
    assert "Invalid file path" in response.json()["detail"]


def test_upload_invalid_signature():
    # Valid extension but invalid magic bytes
    files = {
        "file": (
            "test.docx",
            b"Not a zip file",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = client.post("/api/v1/jobs", files=files)
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]


def test_upload_oversized_file(monkeypatch, mock_job_queue):
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10)
    files = {"file": ("test.docx", b"PK\x03\x04This is too large", "application/octet-stream")}
    response = client.post("/api/v1/jobs", files=files)
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


@patch("app.api.endpoints.jobs.redis_conn")
def test_rate_limiting(mock_redis):
    # Mock redis incr to simulate rate limit exceeded
    mock_redis.incr.return_value = 100
    settings.RATE_LIMIT_CALLS = 10

    files = {"file": ("test.docx", b"PK\x03\x04test", "application/octet-stream")}
    response = client.post("/api/v1/jobs", files=files)
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]


def test_security_headers():
    response = client.get("/api/v1")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Content-Security-Policy") == "default-src 'self'"


def test_cors_behavior():
    # Test valid origin
    headers = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}
    response = client.options("/api/v1/jobs", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_merge_pdfs_success(mock_job_queue):
    fake_job = MagicMock()
    fake_job.id = str(uuid.uuid4())
    mock_job_queue.enqueue.return_value = fake_job

    files = [
        ("files", ("test1.pdf", b"%PDF-1.4\nfake", "application/pdf")),
        ("files", ("test2.pdf", b"%PDF-1.4\nfake", "application/pdf")),
    ]
    response = client.post("/api/v1/jobs/merge", files=files)
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_merge_pdfs_invalid_signature():
    files = [
        ("files", ("test1.pdf", b"%PDF-1.4\nfake", "application/pdf")),
        ("files", ("test2.pdf", b"Not a PDF", "application/pdf")),
    ]
    response = client.post("/api/v1/jobs/merge", files=files)
    assert response.status_code == 400
    assert "Invalid PDF signature" in response.json()["detail"]
