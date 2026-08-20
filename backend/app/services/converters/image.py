from typing import ClassVar

from PIL import Image, ImageOps

from .base import BaseConverter
from .exceptions import ConversionError


class ImageConverter(BaseConverter):
    supported_extensions: ClassVar[set[str]] = {".jpg", ".jpeg", ".png", ".webp"}

    def convert(self) -> str:
        try:
            # Prevent DecompressionBomb errors
            Image.MAX_IMAGE_PIXELS = 100_000_000  # 100 megapixels max

            with Image.open(self.input_path) as img:
                # Validate image content
                img.verify()

            # Reopen after verify
            with Image.open(self.input_path) as img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(img)

                # Convert RGBA to RGB for PDF
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # Save to PDF
                img.save(str(self.output_pdf_path), "PDF", resolution=100.0)

            # Validate output
            self._validate_pdf(self.output_pdf_path)

            return str(self.output_pdf_path)

        except Exception as e:
            raise ConversionError(f"Image conversion failed: {e!s}")
