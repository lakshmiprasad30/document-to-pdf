const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface JobResponse {
  job_id: string;
  status: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  result_id?: string | null;
  error?: string | null;
}

export async function uploadJob(file: File): Promise<JobResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/jobs`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = "Failed to upload file";
    try {
      const data = await response.json();
      if (data.detail) errorMessage = data.detail;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function uploadMergeJob(files: File[]): Promise<JobResponse> {
  const formData = new FormData();
  files.forEach(f => formData.append("files", f));

  const response = await fetch(`${API_URL}/jobs/merge`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = "Failed to merge files";
    try {
      const data = await response.json();
      if (data.detail) errorMessage = data.detail;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_URL}/jobs/${jobId}`);
  
  if (!response.ok) {
    throw new Error("Failed to get job status");
  }

  return response.json();
}

export function getDownloadUrl(resultId: string): string {
  return `${API_URL}/files/${resultId}`;
}
