import shutil
import uuid
from pathlib import Path
from typing import ClassVar

from pypdf import PdfReader

from app.core.config import settings

from .exceptions import (
    CorruptPDFError,
    InputFileNotFoundError,
    OutputFileMissingError,
    UnsupportedFormatError,
)


class BaseConverter:
    supported_extensions: ClassVar[set[str]] = set()

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)
        if not self.input_path.exists():
            raise InputFileNotFoundError("Input file does not exist")

        ext = self.input_path.suffix.lower()
        if ext not in self.supported_extensions:
            raise UnsupportedFormatError(
                f"Extension {ext} is not supported by {self.__class__.__name__}"
            )

        self.job_id = str(uuid.uuid4())
        self.temp_storage = Path(settings.TEMP_STORAGE_PATH)
        self.job_dir = self.temp_storage / self.job_id
        self.job_dir.mkdir(parents=True, exist_ok=True)

        self.output_pdf_path = self.job_dir / f"{self.input_path.stem}.pdf"

    def _validate_pdf(self, pdf_path: Path):
        """Validates that the PDF was generated and is valid."""
        if not pdf_path.exists():
            raise OutputFileMissingError("The expected PDF output was not found.")
        if pdf_path.stat().st_size == 0:
            raise CorruptPDFError("The generated PDF is empty.")

        try:
            reader = PdfReader(str(pdf_path))
            if len(reader.pages) == 0:
                raise CorruptPDFError("The generated PDF has zero pages.")
        except Exception as e:  # noqa: BLE001
            raise CorruptPDFError(f"The generated PDF is corrupt or unreadable: {e!s}")

    def cleanup(self):
        """Cleans up the temporary job directory."""
        if self.job_dir.exists():
            shutil.rmtree(self.job_dir, ignore_errors=True)

    def convert(self) -> str:
        """Converts the input file and returns the path to the resulting PDF."""
        raise NotImplementedError
