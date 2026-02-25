import React from 'react';
import { Download, CheckCircle, X } from 'lucide-react';
import { UploadJob } from '../types';

/**
 * PROCESSING OVERLAY COMPONENT
 * 
 * A full-screen modal that guides the user through the job lifecycle:
 * 1. Physical file upload to S3.
 * 2. Background queueing / Processing on AWS Worker (EC2/SQS/Lambda).
 * 3. Final Result (Download link) or Error handling.
 */

interface ProcessingOverlayProps {
    isProcessing: boolean;
    uploadProgress: number;
    numVariants: number;
    currentJob: UploadJob | null;
    error: string;
    onClose: () => void;
}

const ProcessingOverlay: React.FC<ProcessingOverlayProps> = ({
    isProcessing,
    uploadProgress,
    numVariants,
    currentJob,
    error,
    onClose,
}) => {
    // Determine the current state based on props from App.tsx.
    const isUploading = isProcessing && uploadProgress < 100;
    const isWaitingOrProcessing = isProcessing && uploadProgress >= 100;
    const jobStatus = currentJob?.status;

    /**
     * Map the abstract S3/Worker state to a 0-100% visual progress bar.
     * 
     * Breakdown:
     * - 0-50%: File Upload to S3.
     * - 50-60%: Queued (Waiting for a worker).
     * - 60-99%: Processing (Worker is generating DOCX variants).
     * - 100%: Done.
     */
    const getDisplayProgress = () => {
        if (isUploading) {
            return Math.round(uploadProgress * 0.5);
        }
        if (isWaitingOrProcessing) {
            if (jobStatus === 'Queued') {
                return 55;
            }
            if (jobStatus === 'Processing') {
                return 75;
            }
            return 50;
        }
        if (jobStatus === 'Done') {
            return 100;
        }
        return 0;
    };

    const displayProgress = getDisplayProgress();

    /**
     * Return a localized user-friendly message for the current phase.
     */
    const getStatusMessage = () => {
        if (isUploading) {
            return `Đang tải file lên server (${uploadProgress}%)`;
        }
        if (jobStatus === 'Queued') {
            return 'Đang chờ xử lý...';
        }
        if (jobStatus === 'Processing') {
            return `Đang trộn câu hỏi và tạo ${numVariants} mã đề...`;
        }
        if (uploadProgress >= 100 && isProcessing) {
            return 'Đang khởi tạo...';
        }
        return 'Đang xử lý...';
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center animate-fade-in">
            <div className="bg-white rounded-[32px] p-6 sm:p-8 w-[min(90vw,420px)] shadow-2xl flex flex-col items-center text-center relative animate-scale-up">

                {/* 1. Close Button: Only visible once a terminal state (Done/Error) is reached. */}
                {!isProcessing && (currentJob?.status === 'Done' || error) && (
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X size={20} />
                    </button>
                )}

                {/* 2. ACTIVE PHASE: Uploading or Processing. */}
                {isProcessing && (
                    <>
                        <div className="w-16 h-16 mb-6 relative">
                            {/* Spinner animation logic. */}
                            <div className="absolute inset-0 border-4 border-indigo-100 rounded-full"></div>
                            <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
                        </div>

                        <h3 className="text-xl font-bold text-gray-800 mb-2">Đang xử lý đề thi...</h3>
                        <p className="text-gray-500 mb-6">{getStatusMessage()}</p>

                        {/* Progress Bar UI Component. */}
                        <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-indigo-600 transition-all duration-500 ease-out"
                                style={{ width: `${displayProgress}%` }}
                            >
                                {displayProgress >= 50 && displayProgress < 100 && (
                                    <div className="w-full h-full animate-pulse bg-white/30"></div>
                                )}
                            </div>
                        </div>
                        <p className="text-xs text-gray-400 mt-2">{displayProgress}% hoàn thành</p>
                    </>
                )}

                {/* 3. SUCCESS PHASE: Job Completed. */}
                {!isProcessing && currentJob?.status === 'Done' && (
                    <>
                        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-4 animate-bounce-small">
                            <CheckCircle size={40} className="text-green-600" />
                        </div>
                        <h3 className="text-2xl font-bold text-gray-800 mb-2">Hoàn tất!</h3>
                        <p className="text-gray-500 mb-6">Đã tạo thành công {numVariants} mã đề thi.</p>

                        {/* Primary Call to Action: Download the resulting ZIP package. */}
                        <button
                            onClick={() => window.open(currentJob.outputUrl, '_blank')}
                            className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-purple-200 transition-all flex items-center justify-center gap-2 group"
                        >
                            <Download size={20} className="group-hover:translate-y-1 transition-transform" />
                            Tải kết quả về máy
                        </button>

                        <p className="mt-4 text-xs text-gray-400">
                            File ZIP bao gồm đề thi (.docx) và đáp án (.xlsx)
                        </p>
                    </>
                )}

                {/* 4. ERROR PHASE: Something went wrong. */}
                {!isProcessing && error && (
                    <>
                        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-4">
                            <X size={40} className="text-red-600" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-800 mb-2">Đã xảy ra lỗi</h3>
                        <p className="text-red-500 bg-red-50 p-3 rounded-lg text-sm mb-6 w-full break-words">
                            {error}
                        </p>
                        <button
                            onClick={onClose}
                            className="px-6 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-50"
                        >
                            Đóng và thử lại
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};

export default ProcessingOverlay;
