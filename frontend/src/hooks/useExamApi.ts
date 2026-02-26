import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect, useRef, useCallback } from 'react';
import { api, SubmitJobRequest, JobStatusResponse } from '../services/api';
import { API_BASE_URL } from '../services/api';
import { S3Service } from '../services/s3Service';
import { UploadProgress } from '../types';

/**
 * CACHE KEYS for React Query.
 * Used to manage and invalidate server state cache.
 */
export const queryKeys = {
    jobStatus: (jobId: string) => ['jobStatus', jobId] as const,
    preview: (fileName: string) => ['preview', fileName] as const,
};

/**
 * HOOK: UPLOAD TO S3.
 * Handles the direct multipart/form-data upload to AWS S3 using a temporary 
 * presigned URL provided by the backend.
 */
export const useUploadToS3 = () => {
    return useMutation({
        mutationFn: async ({
            presignedUrl,
            file,
            onProgress,
            contentType,
        }: {
            presignedUrl: string;
            file: File;
            onProgress?: (progress: UploadProgress) => void;
            contentType?: string;
        }) => {
            await S3Service.uploadWithPresignedUrl(file, presignedUrl, onProgress, contentType);
        },
    });
};

/**
 * HOOK: SUBMIT JOB.
 * Sends the processing request to the /submit-job endpoint.
 * On success, it invalidates the job status query to trigger an immediate UI update.
 */
export const useSubmitJob = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (request: SubmitJobRequest) => api.submitJob(request),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.jobStatus(data.jobId) });
        },
    });
};

/**
 * HOOK: JOB STATUS via SSE (Server-Sent Events).
 * Replaces the old polling mechanism.
 * 
 * How it works:
 * - Opens a persistent SSE connection to /api/status/{jobId}/stream.
 * - Server pushes "status" events whenever the job state changes.
 * - Server auto-closes the stream when the job reaches Done/Failed.
 * - Fallback: If SSE connection fails, falls back to a single GET request.
 */
export const useJobStatus = (jobId: string | null, options?: { enabled?: boolean }) => {
    const [data, setData] = useState<JobStatusResponse | undefined>(undefined);
    const eventSourceRef = useRef<EventSource | null>(null);
    const enabled = !!jobId && (options?.enabled ?? true);

    // Cleanup function to close SSE connection
    const cleanup = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (!enabled || !jobId) {
            cleanup();
            return;
        }

        // Build SSE URL
        const sseUrl = `${API_BASE_URL}/api/status/${jobId}/stream`;
        const eventSource = new EventSource(sseUrl);
        eventSourceRef.current = eventSource;

        // Handle "status" events from server
        eventSource.addEventListener('status', (event: MessageEvent) => {
            try {
                const parsed: JobStatusResponse = JSON.parse(event.data);
                setData(parsed);

                // Close connection on terminal states
                if (parsed.Status === 'Done' || parsed.Status === 'Failed') {
                    eventSource.close();
                    eventSourceRef.current = null;
                }
            } catch (err) {
                console.error('[SSE] Failed to parse status event:', err);
            }
        });

        let pollInterval: ReturnType<typeof setInterval>;

        // Handle error events from server
        eventSource.addEventListener('error', () => {
            console.warn('[SSE] Connection error, falling back to polling');
            eventSource.close();
            eventSourceRef.current = null;

            // Fallback: Start polling instead of single GET
            pollInterval = setInterval(async () => {
                try {
                    const parsed = await api.getJobStatus(jobId);
                    setData(parsed);
                    if (parsed.Status === 'Done' || parsed.Status === 'Failed') {
                        clearInterval(pollInterval);
                    }
                } catch (err) {
                    console.error('[Polling Fallback] Error:', err);
                }
            }, 3000);
        });

        return () => {
            cleanup();
            if (pollInterval) {
                clearInterval(pollInterval);
            }
        };
    }, [jobId, enabled, cleanup]);

    // Reset data when jobId changes
    useEffect(() => {
        if (!jobId) {
            setData(undefined);
        }
    }, [jobId]);

    return { data };
};

/**
 * HOOK: PREVIEW EXAM.
 * Calls the backend to parse the uploaded DOCX and return its structured raw text.
 */
export const usePreviewExam = () => {
    return useMutation({
        mutationFn: (file: File) => api.previewExam(file),
    });
};

/**
 * COMBINED HOOK: CREATE JOB WORKFLOW.
 * Orchestrates the 3-step sequence:
 * 1. Get Presigned URL from Backend.
 * 2. Upload physical file to S3.
 * 3. Submit metadata/job-params to SQS via Backend.
 */
export const useCreateJob = () => {
    const uploadToS3 = useUploadToS3();
    const submitJob = useSubmitJob();

    const createJob = async (
        file: File,
        numVariants: number,
        onProgress?: (progress: UploadProgress) => void,
        rawText?: string,
        examCodes?: string
    ): Promise<string> => {
        const contentType = file.type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

        // STEP 1: Handshake with backend to get an S3 upload "ticket".
        const uploadData = await api.getUploadUrl(file.name, contentType);

        // STEP 2: Physical upload.
        await uploadToS3.mutateAsync({
            presignedUrl: uploadData.uploadUrl,
            file,
            onProgress,
            contentType,
        });

        // STEP 3: Submit to queue.
        const jobResult = await submitJob.mutateAsync({
            jobId: uploadData.jobId,
            fileKey: uploadData.fileKey,
            numVariants,
            rawText: rawText,
            examCodes: examCodes,
        });

        return jobResult.jobId;
    };

    return {
        createJob,
        isLoading: uploadToS3.isPending || submitJob.isPending,
        error: uploadToS3.error || submitJob.error,
    };
};
