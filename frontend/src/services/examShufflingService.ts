import { S3Service } from './s3Service';
import { api, SubmitJobRequest } from './api';
import { UploadProgress } from '../types';

/**
 * EXAM SHUFFLING SERVICE
 * 
 * Orchestrates the high-level workflow for creating a variant generation job.
 * Wraps the complex interaction between the Backend (S3 URLs) and the direct S3 uploads.
 */
export class ExamShufflingService {

  /**
   * Main entry point for starting a new shuffling job.
   * Logic flow: 
   * 1. Get S3 lease URL -> 2. Upload file -> 3. Notify backend to start processing.
   */
  static async createJob(
    file: File,
    numVariants: number,
    onUploadProgress?: (progress: UploadProgress) => void
  ): Promise<string> {
    try {
      // PHASE 1: Request a Presigned URL from the Backend API.
      console.log('1. Requesting upload URL...');
      const { jobId, uploadUrl, fileKey } = await api.getUploadUrl(file.name, file.type);

      // PHASE 2: Perform the actual large-file upload to AWS S3 using the URL from Phase 1.
      // This bypasses the backend to ensure high performance and low latency.
      console.log('2. Uploading to S3...');
      await S3Service.uploadWithPresignedUrl(file, uploadUrl, onUploadProgress);

      // PHASE 3: Signal to the backend that the upload is complete.
      // The backend will now place a message on the SQS queue for the Worker to consume.
      console.log('3. Submitting job...');
      const submitData: SubmitJobRequest = {
        jobId,
        fileKey,
        numVariants,
      };
      await api.submitJob(submitData);

      return jobId;
    } catch (error) {
      console.error('Job creation failed:', error);
      throw error;
    }
  }

  /**
   * Fetch current job details from the server.
   */
  static async getJobStatus(jobId: string) {
    return await api.getJobStatus(jobId);
  }
}
