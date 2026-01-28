export interface UploadJob {
  jobId: string;
  fileKey: string;
  fileName: string;
  status: JobStatus;
  createdAt: number;
  updatedAt?: number;
  outputUrl?: string;
  outputKey?: string;
  lastError?: string;
  numVariants: number;
}

export type JobStatus = 'Queued' | 'Processing' | 'Done' | 'Failed';

export interface JobStatusResponse {
  JobId: string;
  Status: JobStatus;
  OutputUrl?: string;
  OutputKey?: string;
  LastError?: string;
  UpdatedAt?: number;
  CreatedAt?: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}
