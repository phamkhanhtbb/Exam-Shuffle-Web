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
  const [previewData, setPreviewData] = useState<{ raw_text: string; assets_map: AssetMap, question_count: number } | null>(null);
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
        setError('Lỗi đọc file: ' + (err instanceof Error ? err.message : String(err)));
        setSelectedFile(null); // Reset file selection to clear zombie state
        setPreviewData(null);
        setUploadProgress(0);
        setShowOverlay(true); // Show overlay to display error? Or just use main error display?
        // Actually, main error display only shows if showOverlay is true OR if we have another mechanism.
        // Looking at render: ProcessingOverlay takes `error` prop.
        // But main layout doesn't show error banner.
        // Let's use setShowOverlay(true) to show the error in the overlay.
        setShowOverlay(true);
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
      // Pass raw_text from Preview to Create Job logic
      const rawText = previewData?.raw_text || '';

      const jobId = await createJob(selectedFile, numVariants, (progress) => {
        setUploadProgress(progress.percentage);
      }, rawText);

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

      // 2. Clear existing * from ALL options (A-H) in this range
      let newLines = [...lines]; // Define newLines here!

      for (let j = startIdx; j < endIdx; j++) {
        // Remove * from *A., *B., ... *H.
        newLines[j] = newLines[j].replace(/(\*)([A-H])([.\\)])/g, '$2$3');
      }

      // 3. Set the new answer using answerLineNumber directly
      if (answerLineNumber && answerLineNumber > 0 && answerLineNumber <= lines.length) {
        const lineIdx = answerLineNumber - 1;
        const targetLine = lines[lineIdx]; // Use ORIGINAL line to check state
        const targetLetter = answer.toUpperCase();

        // Check if it was already selected
        // Regex: (*?)Letter[.)]
        const wasSelectedRegex = new RegExp(`\\*${targetLetter}([.\\)])`);
        const wasSelected = wasSelectedRegex.test(targetLine);

        if (!wasSelected) {
          // Add * to the specific option
          newLines[lineIdx] = newLines[lineIdx].replace(
            new RegExp(`(^|\\s)(${targetLetter})([.\\)])`),
            '$1*$2$3'
          );
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

        // Regex: Find (*?)letter) - STRICT MODE: letter + ')'
        // We only support a-d and ) for True/False now to avoid conflicts.
        const regex = new RegExp(`(\\*?)(${targetLetter})\\)`, 'g');

        if (regex.test(line)) {
          // Check if SPECIFIC option has star
          // We need to be careful not to match *ab) if we look for *b)
          // But with ) boundary it is safe.

          const match = line.match(new RegExp(`\\*${targetLetter}\\)`));
          const hasStar = !!match;

          let newLine = line;

          if (hasStar) {
            // Remove star: *a) -> a)
            newLine = newLine.replace(new RegExp(`\\*${targetLetter}\\)`, 'g'), `${targetLetter})`);
          } else {
            // Add star: a) -> *a)
            // Use word boundary or just the letter+paren
            newLine = newLine.replace(new RegExp(`(^|\\s)(${targetLetter})\\)`, 'g'), `$1*${targetLetter})`);
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

  const handleShortAnswerChange = useCallback((questionIndex: number, text: string, sourceLineNumber: number) => {
    // 1. Update Correct Answers Map
    setCorrectAnswers(prev => {
      const newMap = new Map(prev);
      if (text) newMap.set(questionIndex, text);
      else newMap.delete(questionIndex);
      return newMap;
    });

    // 2. Update Raw Text (Bidirectional Sync)
    setPreviewData(prev => {
      if (!prev) return prev;
      const lines = prev.raw_text.split('\n');

      if (!sourceLineNumber || sourceLineNumber < 1) return prev;
      const startIdx = sourceLineNumber - 1;

      // Find End of Question Block
      let endIdx = lines.length;
      const questionRegex = /(?:\[ID:[^\]]*\]\s*)?Câu\s*\d+/i;

      for (let i = startIdx + 1; i < lines.length; i++) {
        const trimmed = lines[i].trim();
        const upper = trimmed.toUpperCase();

        // Check for End Markers (HẾT, ĐÁP ÁN table header)
        if (/^[-=\s]*HẾT[-=\s]*$/.test(upper) ||
          upper === 'ĐÁP ÁN' ||
          upper === 'BẢNG ĐÁP ÁN' ||
          upper.includes('[!B:ĐÁP ÁN]') // Check for bold tagged markers too
        ) {
          endIdx = i;
          break;
        }

        if (trimmed.match(questionRegex) ||
          trimmed.toLowerCase().includes('phần ii') ||
          trimmed.toLowerCase().includes('phần 2') || // Add Part 2 check variants
          trimmed.toLowerCase().includes('phần iii') ||
          trimmed.toLowerCase().includes('phần 3')) { // Add Part 3 check variants
          endIdx = i;
          break;
        }
      }

      // Look for existing 'Đáp án:' line within [startIdx, endIdx)
      let answerLineIdx = -1;
      const answerRegex = /^Đáp án:/i;

      for (let i = startIdx; i < endIdx; i++) {
        if (answerRegex.test(lines[i].trim())) {
          answerLineIdx = i;
          break;
        }
      }

      const newLines = [...lines];

      if (answerLineIdx !== -1) {
        // Found existing line
        if (text) {
          // Update it
          newLines[answerLineIdx] = `Đáp án: ${text}`;
        } else {
          // If text empty, remove the line? Or keep it empty? 
          // Let's remove it to keep text clean, or just empty "Đáp án:"
          // User request: "adds line...". Implies dynamic.
          // Let's set it to empty for now to avoid jumping structure too much, or delete.
          // Deleting is cleaner for generating clean regex later.
          newLines.splice(answerLineIdx, 1);
        }
      } else {
        // Not found, insert at the end of the block
        if (text) {
          newLines.splice(endIdx, 0, `Đáp án: ${text}`);
        }
      }

      return {
        ...prev,
        raw_text: newLines.join('\n')
      };
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