import axios from 'axios';

// Get API URL from environment variable, default to localhost for development
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const apiClient = axios.create({
    baseURL: API_URL,
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
}

export interface SubmitJobResponse {
    message: string;
    jobId: string;
}

// Job Status Response matching Backend schema
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
     * Request a Presigned URL for S3 Upload
     */
    getUploadUrl: async (fileName: string, fileType: string): Promise<UploadUrlResponse> => {
        const response = await apiClient.post<UploadUrlResponse>('/api/get-upload-url', {
            fileName,
            fileType,
        });
        return response.data;
    },

    /**
     * Submit a job for processing (Trigger SQS)
     */
    submitJob: async (data: SubmitJobRequest): Promise<SubmitJobResponse> => {
        const response = await apiClient.post<SubmitJobResponse>('/api/submit-job', data);
        return response.data;
    },

    /**
     * Get current job status
     */
    getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
        const response = await apiClient.get<JobStatusResponse>(`/api/status/${jobId}`);
        return response.data;
    },
};
