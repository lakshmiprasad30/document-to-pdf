import uuid
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.core.config import settings

from .exceptions import ConversionError


class PdfMergerService:
    def __init__(self, input_paths: list[str]):
        if len(input_paths) < 2:
            raise ConversionError("At least 2 PDFs are required for merging")
        if len(input_paths) > 50:
            raise ConversionError("Maximum of 50 PDFs can be merged at once")

        self.input_paths = [Path(p) for p in input_paths]
        for p in self.input_paths:
            if not p.exists() or p.suffix.lower() != ".pdf":
                raise ConversionError(f"Invalid PDF file: {p.name}")

        self.job_id = str(uuid.uuid4())
        self.temp_storage = Path(settings.TEMP_STORAGE_PATH)
        self.job_dir = self.temp_storage / self.job_id
        self.job_dir.mkdir(parents=True, exist_ok=True)

        self.output_pdf_path = self.job_dir / "merged.pdf"

    def merge(self) -> str:
        merger = PdfWriter()
        try:
            for path in self.input_paths:
                # Basic validation that it is a valid PDF
                reader = PdfReader(str(path))
                if len(reader.pages) == 0:
                    raise ConversionError(f"PDF {path.name} is empty.")
                merger.append(str(path))

            merger.write(str(self.output_pdf_path))
            merger.close()

            # Delete original individual input PDFs to save space
            for path in self.input_paths:
                path.unlink(missing_ok=True)

            return str(self.output_pdf_path)
        except Exception as e:
            raise ConversionError(f"PDF Merge failed: {e!s}")
