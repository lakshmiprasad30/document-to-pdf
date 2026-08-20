from typing import ClassVar

from fpdf import FPDF

from .base import BaseConverter
from .exceptions import ConversionError


class TxtConverter(BaseConverter):
    supported_extensions: ClassVar[set[str]] = {".txt"}

    def convert(self) -> str:
        try:
            # Read UTF-8 text
            content = self.input_path.read_text(encoding="utf-8")

            # Simple line wrapping setup
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            # Use basic Arial or Helvetica
            pdf.set_font("Helvetica", size=11)

            # Split and write lines (multi_cell handles line wrapping automatically)
            pdf.multi_cell(0, 5, content)

            pdf.output(str(self.output_pdf_path))

            # Validate output
            self._validate_pdf(self.output_pdf_path)

            return str(self.output_pdf_path)

        except UnicodeDecodeError:
            raise ConversionError("Text file must be valid UTF-8.")
        except Exception as e:
            raise ConversionError(f"Text conversion failed: {e!s}")
