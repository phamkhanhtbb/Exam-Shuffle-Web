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
 * 
 * How it works:
 * - Opens a persistent SSE connection to /api/status/{jobId}/stream.
 * - Server pushes "status" events whenever the job state changes.
 * - Server auto-closes the stream when the job reaches Done/Failed.
 * - Reconnect: If SSE fails, retries up to 3 times with exponential backoff.
 * - Fallback: After 3 retries, falls back to HTTP polling every 2s.
 */
export const useJobStatus = (jobId: string | null, options?: { enabled?: boolean }) => {
    const [data, setData] = useState<JobStatusResponse | undefined>(undefined);
    const eventSourceRef = useRef<EventSource | null>(null);
    const retryCountRef = useRef(0);
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const enabled = !!jobId && (options?.enabled ?? true);

    const MAX_SSE_RETRIES = 3;

    // Cleanup all connections and timers
    const cleanup = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        if (retryTimerRef.current) {
            clearTimeout(retryTimerRef.current);
            retryTimerRef.current = null;
        }
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }
    }, []);

    // Start fallback polling
    const startPolling = useCallback((currentJobId: string) => {
        if (pollIntervalRef.current) return; // Already polling
        console.warn('[SSE] Max retries reached, falling back to polling (2s)');
        pollIntervalRef.current = setInterval(async () => {
            try {
                const parsed = await api.getJobStatus(currentJobId);
                setData(parsed);
                if (parsed.Status === 'Done' || parsed.Status === 'Failed') {
                    if (pollIntervalRef.current) {
                        clearInterval(pollIntervalRef.current);
                        pollIntervalRef.current = null;
                    }
                }
            } catch (err) {
                console.error('[Polling Fallback] Error:', err);
            }
        }, 2000);
    }, []);

    // Connect or reconnect SSE
    const connectSSE = useCallback((currentJobId: string) => {
        // Clean up any existing connection
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }

        const sseUrl = `${API_BASE_URL}/api/status/${currentJobId}/stream`;
        const eventSource = new EventSource(sseUrl);
        eventSourceRef.current = eventSource;

        eventSource.addEventListener('status', (event: MessageEvent) => {
            try {
                const parsed: JobStatusResponse = JSON.parse(event.data);
                setData(parsed);
                retryCountRef.current = 0; // Reset retry count on successful data

                if (parsed.Status === 'Done' || parsed.Status === 'Failed') {
                    eventSource.close();
                    eventSourceRef.current = null;
                }
            } catch (err) {
                console.error('[SSE] Failed to parse status event:', err);
            }
        });

        eventSource.addEventListener('error', () => {
            eventSource.close();
            eventSourceRef.current = null;
            retryCountRef.current++;

            if (retryCountRef.current <= MAX_SSE_RETRIES) {
                // Exponential backoff: 1s, 2s, 4s
                const delay = Math.pow(2, retryCountRef.current - 1) * 1000;
                console.warn(`[SSE] Connection error, retry ${retryCountRef.current}/${MAX_SSE_RETRIES} in ${delay}ms`);
                retryTimerRef.current = setTimeout(() => {
                    connectSSE(currentJobId);
                }, delay);
            } else {
                startPolling(currentJobId);
            }
        });
    }, [startPolling]);

    useEffect(() => {
        if (!enabled || !jobId) {
            cleanup();
            return;
        }

        retryCountRef.current = 0;
        connectSSE(jobId);

        return () => {
            cleanup();
        };
    }, [jobId, enabled, cleanup, connectSSE]);

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
