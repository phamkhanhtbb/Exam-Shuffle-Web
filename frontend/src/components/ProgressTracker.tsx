import React from 'react';
import { CheckCircle, Clock, AlertCircle, Loader } from 'lucide-react';
import { JobStatus } from '../types';
import './ProgressTracker.css';

interface ProgressTrackerProps {
  status: JobStatus;
  uploadProgress?: number;
  errorMessage?: string;
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  status,
  uploadProgress = 0,
  errorMessage,
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'Queued':
        return {
          icon: <Clock size={24} />,
          label: 'Đang chờ xử lý',
          color: '#f59e0b',
          description: 'Job đang trong hàng đợi...',
        };
      case 'Processing':
        return {
          icon: <Loader size={24} className="spinning" />,
          label: 'Đang xử lý',
          color: '#3b82f6',
          description: 'Đang tạo các đề thi và đáp án...',
        };
      case 'Done':
        return {
          icon: <CheckCircle size={24} />,
          label: 'Hoàn thành',
          color: '#10b981',
          description: 'Xử lý thành công! File đã sẵn sàng để tải về.',
        };
      case 'Failed':
        return {
          icon: <AlertCircle size={24} />,
          label: 'Thất bại',
          color: '#ef4444',
          description: errorMessage || 'Có lỗi xảy ra trong quá trình xử lý.',
        };
      default:
        return {
          icon: <Clock size={24} />,
          label: 'Đang khởi tạo',
          color: '#64748b',
          description: 'Đang chuẩn bị...',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="progress-tracker">
      <div className="progress-header">
        <div className="status-icon" style={{ color: config.color }}>
          {config.icon}
        </div>
        <div className="status-content">
          <h3 style={{ color: config.color }}>{config.label}</h3>
          <p>{config.description}</p>
        </div>
      </div>

      {uploadProgress > 0 && uploadProgress < 100 && (
        <div className="upload-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <span className="progress-text">{uploadProgress}%</span>
        </div>
      )}

      {status === 'Processing' && (
        <div className="processing-steps">
          <div className="step">
            <div className="step-dot completed"></div>
            <span>Upload file</span>
          </div>
          <div className="step">
            <div className="step-dot completed"></div>
            <span>Tạo job</span>
          </div>
          <div className="step">
            <div className="step-dot active"></div>
            <span>Xử lý đề thi</span>
          </div>
          <div className="step">
            <div className="step-dot"></div>
            <span>Tạo file ZIP</span>
          </div>
        </div>
      )}
    </div>
  );
};
