import React, { useState, useRef, DragEvent } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import './FileUpload.css';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  accept?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  disabled = false,
  accept = '.docx',
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="file-upload-container">
      {!selectedFile ? (
        <div
          className={`upload-area ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && fileInputRef.current?.click()}
        >
          <Upload className="upload-icon" size={48} />
          <h3>Kéo thả file vào đây</h3>
          <p>hoặc</p>
          <button className="browse-button" type="button" disabled={disabled}>
            Chọn file từ máy tính
          </button>
          <p className="file-hint">Chỉ chấp nhận file .docx (tối đa 50MB)</p>
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleFileInputChange}
            style={{ display: 'none' }}
            disabled={disabled}
          />
        </div>
      ) : (
        <div className="selected-file">
          <div className="file-info">
            <FileText className="file-icon" size={32} />
            <div className="file-details">
              <h4>{selectedFile.name}</h4>
              <p>{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          {!disabled && (
            <button
              className="remove-button"
              onClick={handleRemoveFile}
              type="button"
            >
              <X size={20} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};
