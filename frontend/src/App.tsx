import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AssetMap } from './components/PreviewRenderer';
import './App.css';

// Import components
import WelcomeSection from './components/WelcomeSection';
import AppHeader from './components/AppHeader';
import PreviewPanel from './components/PreviewPanel';
import EditorPanel, { EditorPanelHandle } from './components/EditorPanel';
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
  const [correctAnswers, setCorrectAnswers] = useState<Map<number, string>>(new Map());
  // State for Part 2 True/False answers - key: "questionIndex-letter", value: true=Đúng, false=Sai
  const [trueFalseAnswers, setTrueFalseAnswers] = useState<Map<string, boolean>>(new Map());

  // Ref for EditorPanel to call scrollToLine
  const editorRef = useRef<EditorPanelHandle>(null);

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
      // Also update correctAnswers from text if user manually edits *A. format
      const newCorrectAnswers = new Map<number, string>();
      const lines = e.target.value.split('\n');
      let currentQuestion = 0;
      for (const line of lines) {
        const questionMatch = line.match(/^Câu\s*(\d+)/i);
        if (questionMatch) {
          currentQuestion = parseInt(questionMatch[1], 10);
        }
        const answerMatch = line.trim().match(/^\*([A-D])[.\)]/);
        if (answerMatch && currentQuestion > 0) {
          newCorrectAnswers.set(currentQuestion, answerMatch[1].toUpperCase());
        }
      }
      setCorrectAnswers(newCorrectAnswers);
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
    setCorrectAnswers(new Map());
    setTrueFalseAnswers(new Map());
  };

  // Handle answer selection from preview
  const handleAnswerSelect = useCallback((questionIndex: number, answer: string) => {
    // Toggle logic: if same answer clicked, deselect it
    const currentlySelected = correctAnswers.get(questionIndex);
    const willBeSelected = currentlySelected === answer ? undefined : answer;

    setCorrectAnswers(prev => {
      const newMap = new Map(prev);
      if (willBeSelected) {
        newMap.set(questionIndex, willBeSelected);
      } else {
        newMap.delete(questionIndex);
      }
      return newMap;
    });

    // Update raw_text to add/remove * prefix
    if (previewData) {
      const lines = previewData.raw_text.split('\n');
      let currentQuestion = 0;

      const newLines = lines.map(line => {
        const questionMatch = line.match(/^Câu\s*(\d+)/i);
        if (questionMatch) {
          currentQuestion = parseInt(questionMatch[1], 10);
        }

        if (currentQuestion === questionIndex) {
          // Handle multiple answers on the same line - ONLY UPPERCASE A, B, C, D
          // eslint-disable-next-line no-useless-escape
          const hasAnswers = /(\*?)([A-D])[.\)]\s*/.test(line);
          if (hasAnswers) {
            // Remove all * prefixes first for this question's answers
            // eslint-disable-next-line no-useless-escape
            let newLine = line.replace(/\*([A-D])([.\)])/g, '$1$2');

            // Add * to the selected answer if any
            if (willBeSelected) {
              // eslint-disable-next-line no-useless-escape
              const selectRegex = new RegExp(`(^|\\s)(${willBeSelected})([.\\)])`, 'gi');
              newLine = newLine.replace(selectRegex, '$1*$2$3');
            }
            return newLine;
          }
        }
        return line;
      });

      setPreviewData({
        ...previewData,
        raw_text: newLines.join('\n')
      });
    }
  }, [previewData, correctAnswers]);

  // Handle True/False toggle for Part 2 (Đúng Sai) questions
  const handleTrueFalseToggle = useCallback((questionIndex: number, letter: string) => {
    const key = `${questionIndex}-${letter}`;
    const currentValue = trueFalseAnswers.get(key) || false;
    const newValue = !currentValue;

    setTrueFalseAnswers(prev => {
      const newMap = new Map(prev);
      if (newValue) {
        newMap.set(key, true);
      } else {
        newMap.delete(key);
      }
      return newMap;
    });

    // Update raw_text to add/remove * prefix for lowercase answers
    if (previewData) {
      const lines = previewData.raw_text.split('\n');
      let currentQuestion = 0;

      const newLines = lines.map(line => {
        const questionMatch = line.match(/^Câu\s*(\d+)/i);
        if (questionMatch) {
          currentQuestion = parseInt(questionMatch[1], 10);
        }

        if (currentQuestion === questionIndex) {
          // Match lowercase a), b), c), d) answers
          // eslint-disable-next-line no-useless-escape
          const answerRegex = new RegExp(`(^|\\s)(\\*?)(${letter.toLowerCase()})\\)`, 'i');
          const match = line.match(answerRegex);
          if (match) {
            if (newValue) {
              // Add * prefix
              return line.replace(answerRegex, `$1*${letter.toLowerCase()})`);
            } else {
              // Remove * prefix
              return line.replace(answerRegex, `$1${letter.toLowerCase()})`);
            }
          }
        }
        return line;
      });

      setPreviewData({
        ...previewData,
        raw_text: newLines.join('\n')
      });
    }
  }, [previewData, trueFalseAnswers]);

  // Handle Short Answer text input (Part 3)
  const handleShortAnswerChange = useCallback((questionIndex: number, text: string) => {
    setCorrectAnswers(prev => {
      const newMap = new Map(prev);
      if (text.trim()) {
        newMap.set(questionIndex, text);
      } else {
        newMap.delete(questionIndex);
      }
      return newMap;
    });
    // Note: Currently we don't sync this back to raw_text because there is no standard format for short answers in the text file yet.
    // We only keep it in React state for now.
  }, []);

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
              correctAnswers={correctAnswers}
              onAnswerSelect={handleAnswerSelect}
              trueFalseAnswers={trueFalseAnswers}
              onTrueFalseToggle={handleTrueFalseToggle}
              onShortAnswerChange={handleShortAnswerChange}
              onLineClick={(lineNumber) => editorRef.current?.scrollToLine(lineNumber)}
            />

            <PaneResizer onMouseDown={startResizing} />

            <EditorPanel
              ref={editorRef}
              width={100 - leftWidth}
              value={previewData?.raw_text || ''}
              onChange={handleTextChange}
              assetsMap={previewData?.assets_map}
              onAssetUpdate={(id, newLatex) => {
                if (previewData && previewData.assets_map) {
                  setPreviewData({
                    ...previewData,
                    assets_map: {
                      ...previewData.assets_map,
                      [id]: {
                        ...previewData.assets_map[id],
                        latex: newLatex
                      }
                    }
                  });
                }
              }}
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