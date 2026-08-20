from pathlib import Path
from typing import Type

from .base import BaseConverter
from .docx import DocxConverter
from .exceptions import UnsupportedFormatError
from .image import ImageConverter
from .pdf import PdfMergerService
from .pptx import PptxConverter
from .txt import TxtConverter
from .xlsx import XlsxConverter

_converters: list[type[BaseConverter]] = [
    DocxConverter,
    XlsxConverter,
    PptxConverter,
    ImageConverter,
    TxtConverter,
]


def get_converter(file_path: str) -> BaseConverter:
    path = Path(file_path)
    ext = path.suffix.lower()

    for converter_class in _converters:
        if ext in converter_class.supported_extensions:
            return converter_class(file_path)

    raise UnsupportedFormatError(f"No converter found for extension {ext}")


__all__ = ["BaseConverter", "PdfMergerService", "UnsupportedFormatError", "get_converter"]
