import React, { useEffect, useState } from 'react';
import './App.css';

// Import components
import WelcomeSection from './components/WelcomeSection';
import AppHeader from './components/AppHeader';
import Workspace from './components/Workspace';
import ProcessingOverlay from './components/ProcessingOverlay';

// Import hooks
import { useCreateJob, useJobStatus, useExamEditor, useResizablePanel, useIsMobile } from './hooks';
import { UploadJob } from './types';

function App() {
  // --- Top-level state ---
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [numVariants, setNumVariants] = useState<number>(10);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [error, setError] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [showOverlay, setShowOverlay] = useState(false);

  // --- Custom hooks ---
  const isMobile = useIsMobile();
  const { leftWidth, containerRef, startResizing } = useResizablePanel(60);
  const {
    previewData,
    correctAnswers,
    trueFalseAnswers,
    editorRef,
    isPreviewLoading,
    handleFilePreview,
    handleTextChange,
    handleLineClick,
    handleAnswerSelect,
    handleTrueFalseToggle,
    handleShortAnswerChange,
    resetEditor,
  } = useExamEditor();

  // React Query hooks
  const { createJob, isLoading: isCreatingJob } = useCreateJob();

  // Auto-polling job status
  const { data: jobStatusData } = useJobStatus(currentJobId, {
    enabled: showOverlay && !!currentJobId,
  });

  // Compute current job from status
  const currentJob: UploadJob | null = jobStatusData ? {
    jobId: jobStatusData.JobId,
    fileKey: '',
    fileName: selectedFile?.name || '',
    status: jobStatusData.Status as 'Queued' | 'Processing' | 'Done' | 'Failed',
    outputUrl: jobStatusData.OutputUrl || '',
    createdAt: jobStatusData.CreatedAt,
    numVariants,
  } : null;

  // Handle job failure
  useEffect(() => {
    if (jobStatusData && jobStatusData.Status === 'Failed') {
      setError('Lỗi xử lý: ' + (jobStatusData.LastError || 'Unknown error'));
    }
  }, [jobStatusData]);

  // Determine if still processing
  const jobStatus = jobStatusData?.Status;
  const isJobComplete = jobStatus === 'Done' || jobStatus === 'Failed';
  const isWaitingForStatus = !!currentJobId && !jobStatusData;
  const isJobRunning = jobStatusData && !isJobComplete;
  const isProcessing = isCreatingJob || isWaitingForStatus || !!isJobRunning;

  // --- HANDLERS ---
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setCurrentJobId(null);
      setError('');
      setUploadProgress(0);

      try {
        await handleFilePreview(file);
      } catch (err) {
        console.error('Preview error:', err);
        setError('Lỗi đọc file: ' + (err instanceof Error ? err.message : String(err)));
        setSelectedFile(null);
        resetEditor();
        setUploadProgress(0);
        setShowOverlay(true);
      }
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    resetEditor();
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
      const rawText = previewData?.raw_text || '';
      const jobId = await createJob(selectedFile, numVariants, (progress) => {
        setUploadProgress(progress.percentage);
      }, rawText);
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
          <Workspace
            previewData={previewData}
            isPreviewLoading={isPreviewLoading}
            editorRef={editorRef}
            isMobile={isMobile}
            leftWidth={leftWidth}
            containerRef={containerRef}
            startResizing={startResizing}
            correctAnswers={correctAnswers}
            trueFalseAnswers={trueFalseAnswers}
            onLineClick={handleLineClick}
            onAnswerSelect={handleAnswerSelect}
            onTrueFalseToggle={handleTrueFalseToggle}
            onShortAnswerChange={handleShortAnswerChange}
            onTextChange={handleTextChange}
          />
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