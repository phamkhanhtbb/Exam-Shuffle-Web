/**
 * API Types - Auto-generated from FastAPI OpenAPI schema
 * These types match the Pydantic models in backend/schemas.py
 */

// === REQUEST TYPES ===

export interface UploadUrlRequest {
    fileName: string;
    fileType?: string;
}

export interface SubmitJobRequest {
    jobId: string;
    fileKey: string;
    numVariants?: number;
}

// === RESPONSE TYPES ===

export interface UploadUrlResponse {
    jobId: string;
    uploadUrl: string;
    fileKey: string;
}

export interface SubmitJobResponse {
    message: string;
    jobId: string;
}

export interface JobStatusResponse {
    JobId: string;
    Status: 'PendingUpload' | 'Queued' | 'Processing' | 'Done' | 'Failed';
    OutputUrl: string | null;
    CreatedAt: number;
    UpdatedAt: number;
    LastError?: string;
}

export interface PreviewData {
    raw_text: string;
    assets_map: Record<string, AssetItem>;
}

export interface PreviewResponse {
    status: 'success' | 'error';
    data: PreviewData;
}

export interface AssetItem {
    type: 'image' | 'math';
    src?: string;
    latex?: string;
    placeholder?: string;
}

export interface ErrorResponse {
    error: string;
    detail?: string;
}

// === UPLOAD PROGRESS ===

export interface UploadProgress {
    loaded: number;
    total: number;
    percentage: number;
}
