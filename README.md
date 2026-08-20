# Document to PDF Converter

A secure, high-performance web application to convert various document and image formats into PDF files. 

## Features

- **Supported Formats**: 
  - Documents: DOCX, XLSX, PPTX, TXT
  - Images: JPG, JPEG, PNG, WEBP
- **Multi-File Uploads**: Convert multiple files in a single batch.
- **PDF Merging**: Combine multiple converted PDFs into a single unified PDF.
- **Progress Tracking**: Real-time polling for individual conversion statuses.
- **Security Hardened**: 
  - Magic byte file signature validation (prevents extension spoofing)
  - Strict path traversal protections
  - IP-based rate limiting via Redis
  - Strict Content Security Policy (CSP) and security headers
  - Non-root unprivileged Docker worker environments
  - Configurable timeouts and maximum file limits
- **Automatic Cleanup**: Background asynchronous sweeping of old artifacts to preserve disk space.

## Architecture

The system uses an asynchronous worker queue architecture for high reliability:

1. **Next.js Frontend**: Lightweight, responsive UI using React and Tailwind CSS.
2. **FastAPI Backend**: Handles incoming REST API requests, validations, and security checks.
3. **Redis**: Acts as a message broker for background tasks and an IP token-bucket for rate limiting.
4. **RQ Worker**: Processes conversions asynchronously, scaling processing power effortlessly.
5. **Converters Factory**: 
   - Uses **LibreOffice (headless)** for parsing DOCX, XLSX, and PPTX
   - Uses **Pillow** for Image formats
   - Uses **fpdf2** for TXT documents
   - Uses **pypdf** for Merging

## Local Setup

### Using Docker (Recommended)

1. Ensure Docker Desktop and Docker Compose are installed.
2. Clone the repository.
3. Start the environment:
   ```bash
   docker compose up -d --build
   ```
4. Access the frontend at `http://localhost:3000`
5. Access the API documentation at `http://localhost:8000/docs`

### Environment Variables

Both `frontend/` and `backend/` have `.env.example` templates. 

**Backend** defaults:
- `REDIS_URL="redis://redis:6379/0"`
- `MAX_FILE_SIZE=52428800` (50MB)
- `RATE_LIMIT_CALLS=10`
- `RATE_LIMIT_WINDOW=60`
- `CLEANUP_TTL_SECONDS=3600`

**Frontend** defaults:
- `NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"`

## API Endpoints

- `POST /api/v1/jobs`
  - Upload a file for conversion (multipart/form-data).
- `POST /api/v1/jobs/merge`
  - Upload multiple `.pdf` files to merge into one (multipart/form-data).
- `GET /api/v1/jobs/{job_id}`
  - Check the status of a specific job (`queued`, `processing`, `completed`, `failed`).
- `GET /api/v1/files/{result_id}`
  - Download a successfully converted or merged PDF.

## Testing

The project contains automated tests verifying security constraints, integration stability, and formatting.

**Backend**:
```bash
cd backend
python -m pytest
ruff check .
```

**Frontend**:
```bash
cd frontend
npm test
npm run lint
```

**End-to-End**:
You can run the end-to-end Python script locally to stress-test the live API:
```bash
cd backend
python test_e2e.py
```

## Known Limitations

- **File Limits**: File size is capped globally at 50MB per upload (configurable).
- **Authentication**: Currently an open MVP. Rate limits exist but authentication/user sessions are out-of-scope for Phase 6.
- **Storage**: Outputs are saved to a temporary local volume, and must be downloaded before the `CLEANUP_TTL_SECONDS` sweeps them. Cloud blob storage (e.g. S3) is not yet integrated.
