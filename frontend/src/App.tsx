import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AssetMap } from './components/PreviewRenderer';
import './App.css';

// Import components
import WelcomeSection from './components/WelcomeSection';
import AppHeader from './components/AppHeader';
import PreviewPanel from './components/PreviewPanel';
import EditorPanel from './components/EditorPanel';
import PaneResizer from './components/PaneResizer';
import ProcessingOverlay from './components/ProcessingOverlay';

// Import React Query hooks
import { useCreateJob, useJobStatus, usePreviewExam } from './hooks';
import { UploadJob } from './types';

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [numVariants, setNumVariants] = useState<number>(10);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{ raw_text: string; assets_map: AssetMap } | null>(null);
  const [error, setError] = useState<string>('');

  // Overlay states
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [showOverlay, setShowOverlay] = useState(false);

  // Resize states
  const [leftWidth, setLeftWidth] = useState(60);
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // React Query hooks
  const { createJob, isLoading: isCreatingJob } = useCreateJob();
  const previewMutation = usePreviewExam();

  // Auto-polling job status
  const { data: jobStatusData } = useJobStatus(currentJobId, {
    enabled: showOverlay && !!currentJobId,
  });

  // Compute current job from status
  const currentJob: UploadJob | null = jobStatusData ? {
    jobId: jobStatusData.JobId,
    fileKey: '', // Not needed for display
    fileName: selectedFile?.name || '',
    status: jobStatusData.Status as 'Queued' | 'Processing' | 'Done' | 'Failed',
    outputUrl: jobStatusData.OutputUrl || '',
    createdAt: jobStatusData.CreatedAt,
    numVariants,
  } : null;

  // Handle job completion or failure
  useEffect(() => {
    if (jobStatusData && jobStatusData.Status === 'Failed') {
      setError('Lỗi xử lý: ' + (jobStatusData.LastError || 'Unknown error'));
    }
  }, [jobStatusData]);

  // Determine if still processing
  // isProcessing = true when:
  // 1. Creating job (uploading + submitting)
  // 2. Waiting for first job status (currentJobId exists but no data yet)
  // 3. Job status is Queued or Processing
  const jobStatus = jobStatusData?.Status;
  const isJobComplete = jobStatus === 'Done' || jobStatus === 'Failed';
  const isWaitingForStatus = !!currentJobId && !jobStatusData;
  const isJobRunning = jobStatusData && !isJobComplete;
  const isProcessing = isCreatingJob || isWaitingForStatus || !!isJobRunning;

  // --- RESIZE LOGIC ---
  const startResizing = useCallback(() => setIsResizing(true), []);
  const stopResizing = useCallback(() => setIsResizing(false), []);

  const resize = useCallback((mouseMoveEvent: MouseEvent) => {
    if (isResizing && containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      let newWidth = ((mouseMoveEvent.clientX - containerRect.left) / containerRect.width) * 100;
      if (newWidth < 20) newWidth = 20;
      if (newWidth > 80) newWidth = 80;
      setLeftWidth(newWidth);
    }
  }, [isResizing]);

  useEffect(() => {
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [resize, stopResizing]);

  // --- HANDLERS ---
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setCurrentJobId(null);
      setError('');
      setUploadProgress(0);

      // Use React Query mutation for preview
      try {
        const result = await previewMutation.mutateAsync(file);
        if (result.status === 'success') {
          setPreviewData(result.data);
        }
      } catch (err) {
        console.error('Preview error:', err);
      }
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (previewData) {
      setPreviewData({
        ...previewData,
        raw_text: e.target.value,
      });
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setCurrentJobId(null);
    setError('');
    setNumVariants(10);
    setUploadProgress(0);
    setShowOverlay(false);
  };

  const closeOverlay = () => {
    if (!isProcessing) {
      setShowOverlay(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    setShowOverlay(true);
    setUploadProgress(0);
    setError('');

    try {
      const jobId = await createJob(selectedFile, numVariants, (progress) => {
        setUploadProgress(progress.percentage);
      });
      setCurrentJobId(jobId);
    } catch (err) {
      setError('Lỗi: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  // --- RENDER ---
  return (
    <div className={`app-container ${selectedFile ? 'mode-workspace' : 'mode-welcome'}`}>
      {/* HEADER */}
      {selectedFile && (
        <AppHeader
          fileName={selectedFile.name}
          numVariants={numVariants}
          isProcessing={isProcessing}
          onNumVariantsChange={setNumVariants}
          onReset={handleReset}
          onSubmit={handleSubmit}
        />
      )}

      {/* MAIN CONTENT */}
      <main className="main-content">
        {!selectedFile && <WelcomeSection onFileChange={handleFileChange} />}

        {selectedFile && (
          <div
            className="workspace-wrapper flex w-full h-full bg-gray-100 overflow-hidden animate-expand"
            ref={containerRef}
          >
            <PreviewPanel
              width={leftWidth}
              isLoading={previewMutation.isPending}
              previewData={previewData}
            />

            <PaneResizer onMouseDown={startResizing} />

            <EditorPanel
              width={100 - leftWidth}
              value={previewData?.raw_text || ''}
              onChange={handleTextChange}
            />
          </div>
        )}
      </main>

      {/* OVERLAY */}
      {showOverlay && (
        <ProcessingOverlay
          isProcessing={isProcessing}
          uploadProgress={uploadProgress}
          numVariants={numVariants}
          currentJob={currentJob}
          error={error}
          onClose={closeOverlay}
        />
      )}
    </div>
  );
}

export default App;