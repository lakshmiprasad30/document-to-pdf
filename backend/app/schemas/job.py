from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result_id: str | None = None
    error: str | None = None
