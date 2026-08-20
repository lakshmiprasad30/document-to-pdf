import shutil
from pathlib import Path

from app.services.converters import get_converter
from app.services.converters.exceptions import ConversionError


def process_job(job_id: str, file_path: str):
    """
    Background job to process a document conversion.
    Supports all registered formats.
    """
    path = Path(file_path)
    if not path.exists():
        return {"job_id": job_id, "status": "failed", "error": "Input file missing."}

    try:
        converter = get_converter(str(path))
        pdf_path = converter.convert()

        # Clean only the profile dir
        profile_dir = converter.job_dir / "lo_profile"
        if profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)

        return {"job_id": job_id, "status": "completed", "output_file": str(pdf_path)}

    except ConversionError as e:
        return {"job_id": job_id, "status": "failed", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"job_id": job_id, "status": "failed", "error": f"Unexpected error: {e!s}"}


def process_merge_job(job_id: str, file_paths: list[str]):
    """
    Background job to process a PDF merge.
    """
    from app.core.config import settings
    from app.services.converters import PdfMergerService

    try:
        merger = PdfMergerService(file_paths)
        # Override job_id so API lookup matches the single enqueued job
        merger.job_id = job_id
        merger.job_dir = Path(settings.TEMP_STORAGE_PATH) / job_id
        merger.job_dir.mkdir(parents=True, exist_ok=True)
        merger.output_pdf_path = merger.job_dir / "merged.pdf"

        pdf_path = merger.merge()

        return {"job_id": job_id, "status": "completed", "output_file": str(pdf_path)}

    except ConversionError as e:
        return {"job_id": job_id, "status": "failed", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"job_id": job_id, "status": "failed", "error": f"Unexpected error: {e!s}"}
