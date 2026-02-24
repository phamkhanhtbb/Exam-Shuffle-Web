import axios from 'axios';

/**
 * AXIOS API CLIENT
 * 
 * Centralized service for all REST communication with the FastAPI backend.
 * Handles:
 * - Environment-based Base URL detection.
 * - Standardized request/response interfaces.
 * - Direct S3 upload orchestration.
 */

// Detect production by hostname, fallback to env var, then localhost for dev.
const isProduction = typeof window !== 'undefined' &&
    (window.location.hostname === 'trondeonline.me' || window.location.hostname === 'www.trondeonline.me');
const API_URL = isProduction
    ? 'https://api.trondeonline.me'
    : (import.meta.env.VITE_API_URL || 'http://localhost:5000');

const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000, // 30 seconds default timeout
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface UploadUrlResponse {
    jobId: string;
    uploadUrl: string;
    fileKey: string;
}

export interface SubmitJobRequest {
    jobId: string;
    fileKey: string;
    numVariants: number;
    rawText?: string;
    examCodes?: string;
}

export interface SubmitJobResponse {
    message: string;
    jobId: string;
}

// Job Status Response matching the Backend 'JobStatusSchema'.
export interface JobStatusResponse {
    JobId: string;
    Status: 'Queued' | 'Processing' | 'Done' | 'Failed';
    OutputUrl?: string;
    CreatedAt: number;
    UpdatedAt: number;
    LastError?: string;
}

export const api = {
    /**
     * Phase 1: Request a Presigned URL for S3 Upload.
     * Tells the backend to generate a temporary write lease for S3.
     */
    getUploadUrl: async (fileName: string, fileType: string): Promise<UploadUrlResponse> => {
        const response = await apiClient.post<UploadUrlResponse>('/api/get-upload-url', {
            fileName,
            fileType,
        });
        return response.data;
    },

    /**
     * Phase 3: Submit a job for processing (Trigger SQS).
     * Called AFTER the file is successfully uploaded to S3.
     */
    submitJob: async (data: SubmitJobRequest): Promise<SubmitJobResponse> => {
        const response = await apiClient.post<SubmitJobResponse>('/api/submit-job', data);
        return response.data;
    },

    /**
     * Status Polling: Retrieve current progress of a background job.
     */
    getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
        const response = await apiClient.get<JobStatusResponse>(`/api/status/${jobId}`);
        return response.data;
    },

    /**
     * Preview Workflow: Instant DOCX -> Text/JSON conversion.
     * Used to show the real-time preview and editor sync.
     */
    previewExam: async (file: File): Promise<any> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await apiClient.post('/api/preview', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 120000, // 120 seconds — parsing DOCX can take a while
        });
        return response.data;
    },
};
