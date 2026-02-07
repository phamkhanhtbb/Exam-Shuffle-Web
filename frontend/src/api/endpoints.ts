import apiClient from './client';
import axios from 'axios';
import {
    UploadUrlRequest,
    UploadUrlResponse,
    SubmitJobRequest,
    SubmitJobResponse,
    JobStatusResponse,
    PreviewResponse,
    UploadProgress,
} from './types';

/**
 * ExamShuffling API endpoints
 */
export const examApi = {
    /**
     * Get presigned URL for file upload
     */
    getUploadUrl: async (request: UploadUrlRequest): Promise<UploadUrlResponse> => {
        const response = await apiClient.post<UploadUrlResponse>('/api/get-upload-url', request);
        return response.data;
    },

    /**
     * Upload file to S3 using presigned URL
     */
    uploadFileToS3: async (
        presignedUrl: string,
        file: File,
        onProgress?: (progress: UploadProgress) => void
    ): Promise<void> => {
        await axios.put(presignedUrl, file, {
            headers: {
                'Content-Type': file.type,
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    onProgress({
                        loaded: progressEvent.loaded,
                        total: progressEvent.total,
                        percentage: Math.round((progressEvent.loaded / progressEvent.total) * 100),
                    });
                }
            },
        });
    },

    /**
     * Submit job for processing
     */
    submitJob: async (request: SubmitJobRequest): Promise<SubmitJobResponse> => {
        const response = await apiClient.post<SubmitJobResponse>('/api/submit-job', request);
        return response.data;
    },

    /**
     * Get job status
     */
    getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
        const response = await apiClient.get<JobStatusResponse>(`/api/status/${jobId}`);
        return response.data;
    },

    /**
     * Preview exam file (upload and parse)
     */
    previewExam: async (file: File): Promise<PreviewResponse> => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await apiClient.post<PreviewResponse>('/api/preview', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    /**
     * Export Excel Answer Key from raw text
     */
    exportKey: async (rawText: string): Promise<Blob> => {
        const response = await apiClient.post('/api/export-key', { raw_text: rawText }, {
            responseType: 'blob'
        });
        return response.data;
    },
};

export default examApi;
