import sys
import time

import requests
from pypdf import PdfReader

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_URL = "https://localhost/api/v1"


def wait_for_job(job_id):
    for i in range(15):
        time.sleep(2)
        status_resp = requests.get(f"{API_URL}/jobs/{job_id}", verify=False)
        status_data = status_resp.json()
        print(f"[{i}] Status for {job_id}:", status_data["status"])
        if status_data["status"] == "completed":
            return status_data
        elif status_data["status"] == "failed":
            print("Job failed:", status_data.get("error"))
            sys.exit(1)
    print("Timeout waiting for job")
    sys.exit(1)


def download_pdf(job_id, filename):
    pdf_resp = requests.get(f"{API_URL}/files/{job_id}", verify=False)
    if pdf_resp.status_code == 200:
        with open(filename, "wb") as pdf_f:
            pdf_f.write(pdf_resp.content)
        print(f"Saved {filename} successfully!")
    else:
        print("Failed to download PDF:", pdf_resp.text)
        sys.exit(1)


def upload_file(filename, mime_type):
    print(f"Uploading {filename}...")
    with open(filename, "rb") as f:
        response = requests.post(
            f"{API_URL}/jobs",
            files={"file": (filename, f, mime_type)},
            verify=False,
        )
    if response.status_code != 200:
        print(f"Upload {filename} failed:", response.text)
        sys.exit(1)
    return response.json()["job_id"]


def test_pipeline():
    # 1. TXT -> PDF
    txt_job_id = upload_file("test.txt", "text/plain")
    wait_for_job(txt_job_id)
    download_pdf(txt_job_id, "out_txt.pdf")

    # 2. JPG -> PDF
    jpg_job_id = upload_file("test.jpg", "image/jpeg")
    wait_for_job(jpg_job_id)
    download_pdf(jpg_job_id, "out_jpg.pdf")

    # 3. DOCX -> PDF
    docx_job_id = upload_file(
        "test_manual.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    wait_for_job(docx_job_id)
    download_pdf(docx_job_id, "out_docx.pdf")

    # 4. Merge PDFs
    print("Merging PDFs...")
    with (
        open("out_txt.pdf", "rb") as f1,
        open("out_jpg.pdf", "rb") as f2,
        open("out_docx.pdf", "rb") as f3,
    ):
        merge_resp = requests.post(
            f"{API_URL}/jobs/merge",
            files=[
                ("files", ("out_txt.pdf", f1, "application/pdf")),
                ("files", ("out_jpg.pdf", f2, "application/pdf")),
                ("files", ("out_docx.pdf", f3, "application/pdf")),
            ],
        )

    if merge_resp.status_code != 200:
        print("Merge failed:", merge_resp.text)
        sys.exit(1)

    merge_job_id = merge_resp.json()["job_id"]
    wait_for_job(merge_job_id)
    download_pdf(merge_job_id, "out_merged.pdf")

    # Verify merged PDF
    reader = PdfReader("out_merged.pdf")
    pages = len(reader.pages)
    print("Pages in merged PDF:", pages)
    if pages < 3:
        print("Merge did not contain all pages")
        sys.exit(1)

    print("All E2E tests passed successfully!")


if __name__ == "__main__":
    test_pipeline()
