import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, SubmitJobRequest, JobStatusResponse } from '../services/api';
import { S3Service } from '../services/s3Service';
import { UploadProgress } from '../types';




// Query keys for cache management
export const queryKeys = {
    jobStatus: (jobId: string) => ['jobStatus', jobId] as const,
    preview: (fileName: string) => ['preview', fileName] as const,
};

/**
 * Hook to upload file to S3 via Presigned URL
 */
export const useUploadToS3 = () => {
    return useMutation({
        mutationFn: async ({
            presignedUrl,
            file,
            onProgress,
        }: {
            presignedUrl: string;
            file: File;
            onProgress?: (progress: UploadProgress) => void;
        }) => {
            await S3Service.uploadWithPresignedUrl(file, presignedUrl, onProgress);
        },
    });
};

/**
 * Hook to submit job for processing
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
 * Hook to poll job status
 */
export const useJobStatus = (jobId: string | null, options?: { enabled?: boolean }) => {
    return useQuery<JobStatusResponse>({
        queryKey: queryKeys.jobStatus(jobId ?? ''),
        queryFn: () => api.getJobStatus(jobId!),
        enabled: !!jobId && (options?.enabled ?? true),
        refetchInterval: (query) => {
            const data = query.state.data as JobStatusResponse | undefined;
            if (data?.Status === 'Done' || data?.Status === 'Failed') {
                return false;
            }
            return 2000;
        },
    });
};

/**
 * Hook to preview exam file (Unified)
 */
export const usePreviewExam = () => {
    return useMutation({
        mutationFn: (file: File) => api.previewExam(file),
    });
};

/**
 * Combined hook for full upload + submit flow
 */
/**
 * Combined hook for full upload + submit flow
 */
export const useCreateJob = () => {
    const uploadToS3 = useUploadToS3();
    const submitJob = useSubmitJob();

    const createJob = async (
        file: File,
        numVariants: number,
        onProgress?: (progress: UploadProgress) => void,
        rawText?: string
    ): Promise<string> => {
        // 1. Get presigned URL
        const uploadData = await api.getUploadUrl(file.name, file.type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');

        // 2. Upload to S3
        await uploadToS3.mutateAsync({
            presignedUrl: uploadData.uploadUrl,
            file,
            onProgress,
        });

        // 3. Submit job
        const jobResult = await submitJob.mutateAsync({
            jobId: uploadData.jobId,
            fileKey: uploadData.fileKey,
            numVariants,
            rawText: rawText // Explicit assignment to avoid shorthand confusion if any
        });

        return jobResult.jobId;
    };

    return {
        createJob,
        isLoading: uploadToS3.isPending || submitJob.isPending,
        error: uploadToS3.error || submitJob.error,
    };
};
