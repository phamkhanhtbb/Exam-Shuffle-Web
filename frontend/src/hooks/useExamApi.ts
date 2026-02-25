import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, SubmitJobRequest, JobStatusResponse } from '../services/api';
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
 * HOOK: JOB STATUS POLLING.
 * Periodically fetches the status of a job from DynamoDB.
 * 
 * Logic:
 * - Polls every 2 seconds.
 * - Auto-stops (refetchInterval: false) once the status is 'Done' or 'Failed'.
 */
export const useJobStatus = (jobId: string | null, options?: { enabled?: boolean }) => {
    return useQuery<JobStatusResponse>({
        queryKey: queryKeys.jobStatus(jobId ?? ''),
        queryFn: () => api.getJobStatus(jobId!),
        enabled: !!jobId && (options?.enabled ?? true),
        refetchInterval: (query) => {
            const data = query.state.data as JobStatusResponse | undefined;
            // Stop polling if terminal state reached.
            if (data?.Status === 'Done' || data?.Status === 'Failed') {
                return false;
            }
            return 2000; // 2 seconds interval.
        },
    });
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
