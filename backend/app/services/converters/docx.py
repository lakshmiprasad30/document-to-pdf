import subprocess
from typing import ClassVar

from app.core.config import settings

from .base import BaseConverter
from .exceptions import ConversionTimeoutError, SubprocessExecutionError


class DocxConverter(BaseConverter):
    supported_extensions: ClassVar[set[str]] = {".docx"}

    def convert(self) -> str:
        try:
            # Create a unique profile dir for LibreOffice to avoid locking issues
            profile_dir = self.job_dir / "lo_profile"
            profile_dir.mkdir(parents=True, exist_ok=True)

            command = [
                "soffice",
                "--headless",
                "--invisible",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                "--nologo",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(self.job_dir),
                str(self.input_path),
                f"-env:UserInstallation=file://{profile_dir}",
            ]

            # Use safe subprocess execution without shell=True
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=settings.MAX_CONVERSION_TIME,
            )

            # Validate output
            self._validate_pdf(self.output_pdf_path)

            return str(self.output_pdf_path)

        except subprocess.TimeoutExpired:
            raise ConversionTimeoutError("LibreOffice conversion timed out.")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore")
            raise SubprocessExecutionError(f"LibreOffice failed: {error_msg}")
