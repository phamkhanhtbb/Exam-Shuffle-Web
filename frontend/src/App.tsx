import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { ProgressTracker } from './components/ProgressTracker';
import { ExamShufflingService } from './services/examShufflingService';
import { UploadJob, JobStatus, UploadProgress, JobStatusResponse } from './types';
import { Download, RefreshCw } from 'lucide-react';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [numVariants, setNumVariants] = useState<number>(10);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
  const [currentStatus, setCurrentStatus] = useState<JobStatus>('Queued');
  const [error, setError] = useState<string>('');

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError('');
    setCurrentJob(null);
  };

  const handleNumVariantsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (value >= 1 && value <= 100) {
      setNumVariants(value);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile) {
      setError('Vui lòng chọn file để upload');
      return;
    }

    setError('');
    setIsProcessing(true);
    setUploadProgress(0);
    setCurrentStatus('Queued');

    try {
      const job = await ExamShufflingService.processFile(selectedFile, {
        numVariants,
        onProgress: (progress: UploadProgress) => {
          setUploadProgress(progress.percentage);
        },
        onStatusChange: (status: JobStatusResponse) => {
          setCurrentStatus(status.Status);
          if (status.Status === 'Done' && status.OutputUrl) {
            setCurrentJob({
              jobId: status.JobId,
              fileKey: '',
              fileName: selectedFile.name,
              status: status.Status,
              createdAt: status.CreatedAt || Date.now(),
              updatedAt: status.UpdatedAt,
              outputUrl: status.OutputUrl,
              outputKey: status.OutputKey,
              numVariants,
            });
          }
        },
      });

      setCurrentJob(job);
      setCurrentStatus(job.status);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
      setCurrentStatus('Failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setCurrentJob(null);
    setError('');
    setUploadProgress(0);
    setCurrentStatus('Queued');
  };

  const handleDownload = () => {
    if (currentJob?.outputUrl) {
      window.open(currentJob.outputUrl, '_blank');
    }
  };

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>🎓 ExamShuffling</h1>
          <p>Hệ thống tự động tạo đề thi trắc nghiệm</p>
        </header>

        <div className="main-content">
          <form onSubmit={handleSubmit} className="upload-form">
            <FileUpload
              onFileSelect={handleFileSelect}
              disabled={isProcessing}
            />

            <div className="form-group">
              <label htmlFor="numVariants">Số lượng đề thi cần tạo:</label>
              <input
                type="number"
                id="numVariants"
                min="1"
                max="100"
                value={numVariants}
                onChange={handleNumVariantsChange}
                disabled={isProcessing}
                className="number-input"
              />
              <p className="input-hint">
                Hệ thống sẽ tạo {numVariants} mã đề khác nhau (từ 101 đến {100 + numVariants})
              </p>
            </div>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <div className="button-group">
              <button
                type="submit"
                disabled={!selectedFile || isProcessing}
                className="submit-button"
              >
                {isProcessing ? 'Đang xử lý...' : 'Bắt đầu xử lý'}
              </button>

              {currentJob && (
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={isProcessing}
                  className="reset-button"
                >
                  <RefreshCw size={18} />
                  Làm mới
                </button>
              )}
            </div>
          </form>

          {(isProcessing || currentJob) && (
            <ProgressTracker
              status={currentStatus}
              uploadProgress={uploadProgress}
              errorMessage={error}
            />
          )}

          {currentJob?.status === 'Done' && currentJob.outputUrl && (
            <div className="result-card">
              <h3>✅ Xử lý thành công!</h3>
              <p>
                Đã tạo thành công {numVariants} mã đề thi và bảng đáp án.
              </p>
              <p className="file-info">
                <strong>File gốc:</strong> {currentJob.fileName}
              </p>
              <button
                onClick={handleDownload}
                className="download-button"
              >
                <Download size={20} />
                Tải về file ZIP
              </button>
              <p className="download-hint">
                File ZIP chứa {numVariants} file docx (mã đề 101-{100 + numVariants}) 
                và 1 file Excel tổng hợp đáp án
              </p>
            </div>
          )}
        </div>

        <footer className="footer">
          <p>
            Powered by AWS S3 + SQS + DynamoDB | 
            Backend: Python + boto3 | 
            Frontend: React + TypeScript
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
