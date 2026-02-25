import React, { useEffect, useState } from 'react';
import './App.css';

/**
 * MAIN ENTRANCE OF THE REACT APPLICATION.
 * This component acts as the 'Orchestrator' of the entire frontend.
 * It manages the global state of the user's workflow: from file selection 
 * to previewing, editing, and eventually submitting the job to the backend.
 */

// -- UI Components --
import WelcomeSection from './components/WelcomeSection';
import AppHeader from './components/AppHeader';
import Workspace from './components/Workspace';
import ProcessingOverlay from './components/ProcessingOverlay';

// -- Custom Logic & Hooks --
// These hooks isolate specific functionalities like API calls, resizing logic, and mobile detection.
import { useCreateJob, useJobStatus, useExamEditor, useResizablePanel, useIsMobile } from './hooks';
import { UploadJob } from './types';

function App() {
  // --- 1. Global Application State ---
  const [selectedFile, setSelectedFile] = useState<File | null>(null);   // The DOCX file currently uploaded.
  const [numVariants, setNumVariants] = useState<number>(10);           // Number of variants requested by user.
  const [examCodes, setExamCodes] = useState<string>('');               // Custom exam codes (comma-separated).
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);// Tracks the active background job ID.
  const [error, setError] = useState<string>('');                       // Global error message for UI display.
  const [uploadProgress, setUploadProgress] = useState<number>(0);      // Progress of file upload to S3 (0-100).
  const [showOverlay, setShowOverlay] = useState(false);                // Toggles the processing/status modal.

  // --- 2. Functional Hooks ---
  const isMobile = useIsMobile();

  // Resizable panel logic for the Editor/Preview side-by-side view.
  const { leftWidth, containerRef, startResizing } = useResizablePanel(60);

  // Core logic for DOCX parsing, text editing, and answer marking.
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

  // React Query hook to trigger the backend processing job.
  const { createJob, isLoading: isCreatingJob } = useCreateJob();

  // Periodic status polling of the currentJobId.
  const { data: jobStatusData } = useJobStatus(currentJobId, {
    enabled: showOverlay && !!currentJobId,
  });

  // --- 3. Derived State & Logic ---

  // Build a model of the current job for the UI based on status data.
  const currentJob: UploadJob | null = jobStatusData ? {
    jobId: jobStatusData.JobId,
    fileKey: '',
    fileName: selectedFile?.name || '',
    status: jobStatusData.Status as 'Queued' | 'Processing' | 'Done' | 'Failed',
    outputUrl: jobStatusData.OutputUrl || '',
    createdAt: jobStatusData.CreatedAt,
    numVariants,
  } : null;

  // Sync processing errors from the polling result to the UI state.
  useEffect(() => {
    if (jobStatusData && jobStatusData.Status === 'Failed') {
      setError('Lỗi xử lý: ' + (jobStatusData.LastError || 'Unknown error'));
    }
  }, [jobStatusData]);

  // Combined processing status to determine UI interactivity.
  const jobStatus = jobStatusData?.Status;
  const isJobComplete = jobStatus === 'Done' || jobStatus === 'Failed';
  const isWaitingForStatus = !!currentJobId && !jobStatusData;
  const isJobRunning = jobStatusData && !isJobComplete;
  const isProcessing = isCreatingJob || isWaitingForStatus || !!isJobRunning;

  // --- 4. Event Handlers ---

  /**
   * Triggers when a user selects a file from the welcome screen or header.
   * Immediately starts the 'Preview' flow to parse and display the document.
   */
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

  /** Resets the entire app to the initial 'Welcome' state. */
  const handleReset = () => {
    setSelectedFile(null);
    resetEditor();
    setCurrentJobId(null);
    setError('');
    setNumVariants(10);
    setExamCodes('');
    setUploadProgress(0);
    setShowOverlay(false);
  };

  const closeOverlay = () => {
    if (!isProcessing) {
      setShowOverlay(false);
    }
  };

  /**
   * Submits the job to the backend:
   * 1. Uploads the file (if changed) or sends the edited raw text.
   * 2. Triggers SQS queue via the /submit-job API.
   * 3. Opens the overlay to track progress.
   */
  const handleSubmit = async () => {
    if (!selectedFile) return;
    setShowOverlay(true);
    setUploadProgress(0);
    setError('');

    try {
      const rawText = previewData?.raw_text || '';
      const jobId = await createJob(selectedFile, numVariants, (progress) => {
        setUploadProgress(progress.percentage);
      }, rawText, examCodes || undefined);
      setCurrentJobId(jobId);
    } catch (err) {
      setError('Lỗi: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  // --- 5. Render Logic ---
  return (
    <div className={`app-container ${selectedFile ? 'mode-workspace' : 'mode-welcome'}`}>

      {/* 5.1 HEADER: Only shown when a file is active. Contains action buttons and job settings. */}
      {selectedFile && (
        <AppHeader
          fileName={selectedFile.name}
          numVariants={numVariants}
          examCodes={examCodes}
          isProcessing={isProcessing}
          onNumVariantsChange={setNumVariants}
          onExamCodesChange={setExamCodes}
          onReset={handleReset}
          onSubmit={handleSubmit}
        />
      )}

      {/* 5.2 MAIN CONTENT: Switches between Welcome Screen and the Workspace. */}
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

      {/* 5.3 STATUS OVERLAY: Shows upload progress and job status (Queued/Processing/Done). */}
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
