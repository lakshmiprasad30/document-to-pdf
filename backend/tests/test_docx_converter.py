import subprocess
from pathlib import Path

import pytest

from app.services.converters.docx import DocxConverter
from app.services.converters.exceptions import (
    ConversionTimeoutError,
    CorruptPDFError,
    InputFileNotFoundError,
    OutputFileMissingError,
    UnsupportedFormatError,
)


@pytest.fixture
def sample_docx(tmp_path):
    file_path = tmp_path / "test.docx"
    file_path.write_text("fake docx content")
    return file_path


@pytest.fixture
def mock_pdf_reader(monkeypatch):
    class MockReader:
        def __init__(self, *args, **kwargs):
            self.pages = [1]  # Fake 1 page

    monkeypatch.setattr("app.services.converters.base.PdfReader", MockReader)


@pytest.fixture
def mock_libreoffice(monkeypatch, mock_pdf_reader):
    def mock_run(*args, **kwargs):
        outdir_idx = args[0].index("--outdir") + 1
        outdir = args[0][outdir_idx]
        input_file = Path(args[0][-2])
        output_pdf = Path(outdir) / f"{input_file.stem}.pdf"
        output_pdf.write_bytes(b"fake valid pdf content")
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", mock_run)


def test_docx_converter_valid(sample_docx, mock_libreoffice):
    converter = DocxConverter(str(sample_docx))
    pdf_path = converter.convert()
    assert Path(pdf_path).exists()
    assert Path(pdf_path).suffix == ".pdf"


def test_docx_converter_missing_input():
    with pytest.raises(InputFileNotFoundError):
        DocxConverter("nonexistent.docx")


def test_docx_converter_unsupported_extension(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello")
    with pytest.raises(UnsupportedFormatError):
        DocxConverter(str(txt_file))


def test_docx_converter_cleanup(sample_docx, mock_libreoffice):
    converter = DocxConverter(str(sample_docx))
    converter.convert()
    assert converter.job_dir.exists()
    converter.cleanup()
    assert not converter.job_dir.exists()


def test_docx_converter_timeout(sample_docx, monkeypatch):
    def mock_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(subprocess, "run", mock_timeout)

    converter = DocxConverter(str(sample_docx))
    with pytest.raises(ConversionTimeoutError):
        converter.convert()


def test_docx_converter_corrupt_pdf(sample_docx, monkeypatch):
    def mock_run_bad_pdf(*args, **kwargs):
        outdir_idx = args[0].index("--outdir") + 1
        outdir = args[0][outdir_idx]
        input_file = Path(args[0][-2])
        output_pdf = Path(outdir) / f"{input_file.stem}.pdf"
        output_pdf.write_bytes(b"")  # 0 bytes triggers CorruptPDFError
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", mock_run_bad_pdf)

    converter = DocxConverter(str(sample_docx))
    with pytest.raises(CorruptPDFError):
        converter.convert()


def test_docx_converter_missing_output(sample_docx, monkeypatch):
    def mock_run_no_output(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", mock_run_no_output)

    converter = DocxConverter(str(sample_docx))
    with pytest.raises(OutputFileMissingError):
        converter.convert()
