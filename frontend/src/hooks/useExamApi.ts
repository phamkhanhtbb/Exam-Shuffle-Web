import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { examApi } from '../api';
import {
    UploadUrlRequest,
    SubmitJobRequest,
    UploadProgress,
    JobStatusResponse
} from '../api/types';

// Query keys for cache management
export const queryKeys = {
    jobStatus: (jobId: string) => ['jobStatus', jobId] as const,
    preview: (fileName: string) => ['preview', fileName] as const,
};

/**
 * Hook to get presigned upload URL
 */
export const useGetUploadUrl = () => {
    return useMutation({
        mutationFn: (request: UploadUrlRequest) => examApi.getUploadUrl(request),
    });
};

/**
 * Hook to upload file to S3
 */
export const useUploadToS3 = () => {
    return useMutation({
        mutationFn: ({
            presignedUrl,
            file,
            onProgress,
        }: {
            presignedUrl: string;
            file: File;
            onProgress?: (progress: UploadProgress) => void;
        }) => examApi.uploadFileToS3(presignedUrl, file, onProgress),
    });
};

/**
 * Hook to submit job for processing
 */
export const useSubmitJob = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (request: SubmitJobRequest) => examApi.submitJob(request),
        onSuccess: (data) => {
            // Invalidate job status query to trigger refetch
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
        queryFn: () => examApi.getJobStatus(jobId!),
        enabled: !!jobId && (options?.enabled ?? true),
        refetchInterval: (query) => {
            const data = query.state.data as JobStatusResponse | undefined;
            // Stop polling when job is done or failed
            if (data?.Status === 'Done' || data?.Status === 'Failed') {
                return false;
            }
            return 2000; // Poll every 2 seconds
        },
    });
};

/**
 * Hook to preview exam file
 */
export const usePreviewExam = () => {
    return useMutation({
        mutationFn: (file: File) => examApi.previewExam(file),
    });
};

/**
 * Combined hook for full upload + submit flow
 */
export const useCreateJob = () => {
    const getUploadUrl = useGetUploadUrl();
    const uploadToS3 = useUploadToS3();
    const submitJob = useSubmitJob();

    const createJob = async (
        file: File,
        numVariants: number,
        onProgress?: (progress: UploadProgress) => void,
        rawText?: string
    ): Promise<string> => {
        // 1. Get presigned URL
        const uploadData = await getUploadUrl.mutateAsync({
            fileName: file.name,
            fileType: file.type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        });

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
            rawText,
        });

        return jobResult.jobId;
    };

    return {
        createJob,
        isLoading: getUploadUrl.isPending || uploadToS3.isPending || submitJob.isPending,
        error: getUploadUrl.error || uploadToS3.error || submitJob.error,
    };
};
