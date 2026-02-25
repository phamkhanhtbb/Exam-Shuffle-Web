import React, { useState, useRef, DragEvent } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import './FileUpload.css';

/**
 * FILE UPLOAD COMPONENT
 * 
 * Handles the initial ingestion of the DOCX file.
 * Supports both drag-and-drop and manual file browsing.
 */

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

  // -- Drag and Drop Handlers --

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

  /**
   * Internal helper to update state and notify the parent component (App.tsx).
   */
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

  /**
   * Resets the input so the user can select a different file.
   */
  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  /**
   * Converts raw bytes to a human-readable string (KB, MB).
   */
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
        /* 1. DROP ZONE: Visible when no file is selected. */
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
          {/* Hidden native file input element. */}
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
        /* 2. FILE PREVIEW: Visible after a file has been selected. */
        <div className="selected-file">
          <div className="file-info">
            <FileText className="file-icon" size={32} />
            <div className="file-details">
              <h4>{selectedFile.name}</h4>
              <p>{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          {/* Action button to clear the selection. */}
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
