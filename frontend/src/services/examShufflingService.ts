import { S3Service } from './s3Service';
import { api, SubmitJobRequest } from './api';
import { UploadProgress } from '../types';

export class ExamShufflingService {

  static async createJob(
    file: File,
    numVariants: number,
    onUploadProgress?: (progress: UploadProgress) => void
  ): Promise<string> {
    try {
      // BƯỚC 1: Xin Presigned URL từ Backend
      console.log('1. Requesting upload URL...');
      const { jobId, uploadUrl, fileKey } = await api.getUploadUrl(file.name, file.type);

      // BƯỚC 2: Upload file lên S3 dùng URL vừa xin được
      console.log('2. Uploading to S3...');
      await S3Service.uploadWithPresignedUrl(file, uploadUrl, onUploadProgress);

      // BƯỚC 3: Báo cho Backend biết đã upload xong để đẩy vào Queue
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

  static async getJobStatus(jobId: string) {
    return await api.getJobStatus(jobId);
  }
}
