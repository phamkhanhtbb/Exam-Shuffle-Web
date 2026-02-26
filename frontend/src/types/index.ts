/**
 * SHARED TYPES AND INTERFACES
 * 
 * Defines the common data structures used across the frontend:
 * 1. API Response types (re-exported).
 * 2. Internal Job Status states.
 * 3. The main 'UploadJob' model used for state management.
 */

// Re-export API types for easy access in components.
export type { JobStatusResponse, UploadProgress } from '../api/types';

// Finite state machine for the Job Lifecycle.
export type JobStatus = 'PendingUpload' | 'Queued' | 'Processing' | 'Done' | 'Failed';

/**
 * Main domain model for a single shuffling request.
 * Persisted in local state and tracked via React Query.
 */
export interface UploadJob {
  jobId: string;
  fileKey: string;      // S3 Key for the original DOCX file
  fileName: string;
  status: JobStatus;
  jobProgress?: number;
  createdAt: number;
  updatedAt?: number;
  outputUrl?: string;   // S3 Presigned URL for the resulting ZIP
  outputKey?: string;   // S3 Key for the resulting ZIP
  lastError?: string;
  numVariants: number;
}
