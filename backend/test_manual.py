import docx

from app.worker.tasks import process_job

print("Creating test.docx...")
doc = docx.Document()
doc.add_paragraph("Hello, LibreOffice!")
doc.save("test_manual.docx")


print("Starting manual job...")
result = process_job("manual-job-1", "test_manual.docx")
print("Result:", result)

from pypdf import PdfReader

if "output_file" in result:
    pdf_path = result["output_file"]
    print(f"Opening {pdf_path}")
    reader = PdfReader(pdf_path)
    print(f"Pages: {len(reader.pages)}")
