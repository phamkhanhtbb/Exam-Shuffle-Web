// Re-export API types
export type { JobStatusResponse, UploadProgress } from '../api/types';

// Status type for internal use
export type JobStatus = 'PendingUpload' | 'Queued' | 'Processing' | 'Done' | 'Failed';

// Local types
export interface UploadJob {
  jobId: string;
  fileKey: string;
  fileName: string;
  status: 'PendingUpload' | 'Queued' | 'Processing' | 'Done' | 'Failed';
  createdAt: number;
  updatedAt?: number;
  outputUrl?: string;
  outputKey?: string;
  lastError?: string;
  numVariants: number;
}
