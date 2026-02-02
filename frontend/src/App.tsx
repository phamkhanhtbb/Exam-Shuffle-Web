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

  // Interaction State
  const [correctAnswers, setCorrectAnswers] = useState<Map<number, string>>(new Map());
  const [trueFalseAnswers, setTrueFalseAnswers] = useState<Map<string, boolean>>(new Map());
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
      setPreviewData({
        ...previewData,
        raw_text: e.target.value,
      });
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setCorrectAnswers(new Map());
    setCorrectAnswers(new Map());
    setTrueFalseAnswers(new Map());
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

  // --- INTERACTION HANDLERS ---
  const handleLineClick = useCallback((lineNumber: number) => {
    if (editorRef.current) {
      editorRef.current.scrollToLine(lineNumber);
    }
  }, []);

  const handleAnswerSelect = useCallback((_questionIndex: number, answer: string, sourceLineNumber: number, answerLineNumber: number) => {
    // 0. Scroll to answer line
    if (editorRef.current && answerLineNumber) {
      editorRef.current.scrollToLine(answerLineNumber);
    }

    // 1. Update Preview Data (Raw Text) for Bidirectional Edit
    setPreviewData(prev => {
      if (!prev) return prev;

      // Split lines to find valid range. sourceLineNumber is 1-based.
      const lines = prev.raw_text.split('\n');
      const startIdx = sourceLineNumber - 1;

      // Search boundaries: from startIdx until next "Câu" or Part header or End
      let endIdx = lines.length;
      const questionRegex = /^Câu\s*\d+/i;

      for (let i = startIdx + 1; i < lines.length; i++) {
        const trimmed = lines[i].trim();
        if (trimmed.match(questionRegex) ||
          trimmed.toLowerCase().includes('phần ii') ||
          trimmed.toLowerCase().includes('phần iii')) {
          endIdx = i;
          break;
        }
      }

      // Search for the specific answer line (A., B., C., D.) to toggle '*'
      // Pattern: (*?)<Letter>[.)]
      const targetLetter = answer.toUpperCase();
      let newLines = [...lines];

      for (let i = startIdx; i < endIdx; i++) {
        const line = newLines[i];
        const trimmed = line.trim();

        // Check if this line contains the target answer label
        // Regex to find "A." or "*A." or "A)" at start or after space
        // Careful not to match "A." inside text content if possible, but standard format is rigid.
        // Simple check: start of line or after pipe/space

        // Regex: Find the Label Pattern for THIS answer
        // Group 1: Optional '*'
        // Group 2: The Letter
        const regex = new RegExp(`(\\*?)(${targetLetter})([.\\)])`, 'g');

        if (regex.test(trimmed)) {
          // Determine if we are adding or removing
          // If currently has *, remove it. If not, add it.
          // BUT: We must also remove * from valid siblings if single choice logic?
          // The user request says "thêm *". Implicitly implies single choice toggle or multi?
          // Usually MCQ is single choice. Let's assume single choice for now: 
          //    Clear * from other options in this question range, Set * on this one.
          //    OR just toggle if it's the same.

          // Let's implement toggle logic for the clicked one, and if it's new, clear others.

          // Strategy: Rebuild the lines in this range.

          // 1. Clear existing * from A/B/C/D in this range
          for (let j = startIdx; j < endIdx; j++) {
            // Remove * from A., B., C., D.
            newLines[j] = newLines[j].replace(/(\*)([A-D])([.\\)])/g, '$2$3');
          }

          // 2. Add * to the specific target if it wasn't already selected (logic check needed?)
          // Actually sync logic: 
          // If previous state had this answer, we are deselecting -> Done (already cleared above)
          // If previous state different or null -> Add *

          // Check if we effectively 'deselected' by clearing using previous state logic is tricky 
          // because we just wiped the text markers. 
          // Better: Check the SPECIFIC line before clearing.

          const wasSelected = line.includes(`*${targetLetter}`);
          if (!wasSelected) {
            // Add * back to this specific instance
            // Use loop j again or just modify current line?
            // Need to be careful if multiple options on one line.
            newLines[i] = newLines[i].replace(
              new RegExp(`(^|\\s)(${targetLetter})([.\\)])`),
              '$1*$2$3'
            );
          }
          break; // Handled
        }
      }

      return {
        ...prev,
        raw_text: newLines.join('\n')
      };
    });
  }, []);

  const handleTrueFalseToggle = useCallback((_questionIndex: number, letter: string, _sourceLineNumber: number, answerLineNumber: number) => {
    // 0. Scroll to answer line
    if (editorRef.current && answerLineNumber) {
      editorRef.current.scrollToLine(answerLineNumber);
    }

    // 1. Update Preview Data (Text)
    setPreviewData(prev => {
      if (!prev) return prev;
      const lines = prev.raw_text.split('\n');
      // answerLineNumber is 1-based, so index is -1
      const lineIdx = answerLineNumber - 1;

      if (lineIdx >= 0 && lineIdx < lines.length) {
        const line = lines[lineIdx];
        const targetLetter = letter.toLowerCase();

        // Regex to find "a)" or "*a)"
        // We just need to toggle the * prefix for THIS letter.
        // Be careful if multiple answers on one line (though rare for T/F).
        // Usually T/F options are: a) ... b) ...

        // Regex: Find (*?)letter)
        const regex = new RegExp(`(\\*?)(${targetLetter})\\)`, 'g');

        if (regex.test(line)) {
          // If it has *, remove it. If not, add it.
          // Note: The previous logic had tri-state (True/False/Off).
          // But for Text Sync, we only map "True" -> "*" and "False/Off" -> "" (no star).
          // So acts as a simple toggle of the star.

          const hasStar = line.includes(`*${targetLetter})`);
          let newLine = line;

          if (hasStar) {
            // Remove star: *a) -> a)
            newLine = line.replace(
              new RegExp(`\\*${targetLetter}\\)`, 'g'),
              `${targetLetter})`
            );
          } else {
            // Add star: a) -> *a)
            // Check boundaries to avoid matching inside words? 
            // Usually " a)" or "^a)"
            newLine = line.replace(
              new RegExp(`(^|\\s)(${targetLetter})\\)`, 'g'),
              `$1*${targetLetter})`
            );
          }

          if (newLine !== line) {
            const newLines = [...lines];
            newLines[lineIdx] = newLine;
            return {
              ...prev,
              raw_text: newLines.join('\n')
            };
          }
        }
      }
      return prev;
    });
  }, []);

  const handleShortAnswerChange = useCallback((questionIndex: number, text: string) => {
    setCorrectAnswers(prev => {
      const newMap = new Map(prev);
      if (text) newMap.set(questionIndex, text);
      else newMap.delete(questionIndex);
      return newMap;
    });
  }, []);

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
              onLineClick={handleLineClick}
              onAnswerSelect={handleAnswerSelect}
              correctAnswers={correctAnswers}
              onTrueFalseToggle={handleTrueFalseToggle}
              trueFalseAnswers={trueFalseAnswers}
              onShortAnswerChange={handleShortAnswerChange} // Pass handler
            />

            <PaneResizer onMouseDown={startResizing} />

            <EditorPanel
              ref={editorRef}
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