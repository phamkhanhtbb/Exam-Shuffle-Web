import { useCallback, useRef, useState } from 'react';
import { AssetMap } from '../components/PreviewRenderer';
import { EditorPanelHandle } from '../components/EditorPanel';
import { usePreviewExam } from './useExamApi';

/**
 * Data structure for the parsed exam template.
 */
export interface PreviewData {
    raw_text: string;      // The raw text content of the DOCX.
    assets_map: AssetMap;  // Map of image/math resources.
    question_count: number;
}

/**
 * Interface defining the actions and state provided by the useExamEditor hook.
 */
export interface ExamEditorActions {
    previewData: PreviewData | null;
    correctAnswers: Map<number, string>;
    trueFalseAnswers: Map<string, boolean>;
    editorRef: React.RefObject<EditorPanelHandle>;
    isPreviewLoading: boolean;
    handleFilePreview: (file: File) => Promise<void>;
    handleTextChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    handleLineClick: (lineNumber: number) => void;
    handleAnswerSelect: (
        questionIndex: number,
        answer: string,
        sourceLineNumber: number,
        answerLineNumber: number
    ) => void;
    handleTrueFalseToggle: (
        questionIndex: number,
        letter: string,
        sourceLineNumber: number,
        answerLineNumber: number
    ) => void;
    handleShortAnswerChange: (
        questionIndex: number,
        text: string,
        sourceLineNumber: number
    ) => void;
    resetEditor: () => void;
}

/**
 * CORE HOOK: BI-DIRECTIONAL EDITOR LOGIC.
 * This hook manages the synchronization between the raw text (Editor) and 
 * the interactive components (Preview).
 * 
 * Flow:
 * 1. User uploads file -> Backend parses it -> Returns 'rawText'.
 * 2. User edits text -> Preview updates in real-time.
 * 3. User clicks an answer in Preview -> `rawText` is modified (e.g., adding '*') 
 *    and Editor scrolls to the line.
 */
export function useExamEditor(): ExamEditorActions {
    // -- State --
    const [previewData, setPreviewData] = useState<PreviewData | null>(null);
    const [correctAnswers, setCorrectAnswers] = useState<Map<number, string>>(new Map());
    const [trueFalseAnswers, setTrueFalseAnswers] = useState<Map<string, boolean>>(new Map());

    // Reference to the editor to trigger scrolling.
    const editorRef = useRef<EditorPanelHandle>(null);

    // API Hook for parsing the DOCX file.
    const previewMutation = usePreviewExam();
    // Use a ref so that handleFilePreview doesn't recreate on every mutation state change.
    const previewMutationRef = useRef(previewMutation);
    previewMutationRef.current = previewMutation;

    // --- 1. File Preview & Initial Parsing ---
    const handleFilePreview = useCallback(async (file: File) => {
        const result = await previewMutationRef.current.mutateAsync(file);
        if (result.status === 'success') {
            setPreviewData(result.data);

            // AUTO-RECOVERY: Extract any existing short answers from the raw text.
            const initialAnswers = new Map<number, string>();
            const rawLines = result.data.raw_text.split('\n');
            let currentQIndex = 0;
            const qRegex = /(?:\[ID:[^\]]*\]\s*)?Câu\s*(\d+)/i;
            const ansRegex = /^Đáp án:\s*(.+)/i;

            for (const line of rawLines) {
                const qMatch = line.match(qRegex);
                if (qMatch) {
                    currentQIndex = parseInt(qMatch[1], 10);
                }
                const ansMatch = line.trim().match(ansRegex);
                if (ansMatch && currentQIndex > 0) {
                    initialAnswers.set(currentQIndex, ansMatch[1].trim());
                }
            }

            if (initialAnswers.size > 0) {
                setCorrectAnswers(initialAnswers);
            }
        }
    }, [previewMutation]);

    // --- 2. Real-time Text Updates ---
    const handleTextChange = useCallback(
        (e: React.ChangeEvent<HTMLTextAreaElement>) => {
            setPreviewData((prev) => {
                if (!prev) return prev;
                return { ...prev, raw_text: e.target.value };
            });
        },
        []
    );

    // --- 3. Navigation Sync ---
    const handleLineClick = useCallback((lineNumber: number) => {
        if (editorRef.current) {
            editorRef.current.scrollToLine(lineNumber);
        }
    }, []);

    // --- 4. MCQ Answer Marking Logic (Preview -> Editor) ---
    /**
     * When a user clicks 'A', 'B', 'C', or 'D' in the Preview:
     * 1. Locate the correct line in `rawText`.
     * 2. Insert an asterisk (*) before the selected letter.
     * 3. Remove asterisks from other siblings in the same question.
     */
    const handleAnswerSelect = useCallback(
        (
            _questionIndex: number,
            answer: string,
            sourceLineNumber: number,
            answerLineNumber: number
        ) => {
            // Scroll editor to the line where the user clicked.
            if (editorRef.current && answerLineNumber) {
                editorRef.current.scrollToLine(answerLineNumber);
            }

            setPreviewData((prev) => {
                if (!prev) return prev;

                const lines = prev.raw_text.split('\n');
                const startIdx = sourceLineNumber - 1;

                // Determine the boundaries of the current question.
                let endIdx = lines.length;
                const questionRegex = /^Câu\s*\d+/i;

                for (let i = startIdx + 1; i < lines.length; i++) {
                    const trimmed = lines[i].trim();
                    if (
                        trimmed.match(questionRegex) ||
                        trimmed.toLowerCase().includes('phần ii') ||
                        trimmed.toLowerCase().includes('phần iii')
                    ) {
                        endIdx = i;
                        break;
                    }
                }

                // STEP 1: Clear existing selection marker (*) from all options A-H.
                const newLines = [...lines];
                for (let j = startIdx; j < endIdx; j++) {
                    newLines[j] = newLines[j].replace(/(\*)([A-D])([.\\)])/g, '$2$3');
                }

                // STEP 2: Inject the asterisk (*) for the newly selected option.
                if (answerLineNumber && answerLineNumber > 0 && answerLineNumber <= lines.length) {
                    const lineIdx = answerLineNumber - 1;
                    const targetLine = lines[lineIdx];
                    const targetLetter = answer.toUpperCase();

                    const wasSelectedRegex = new RegExp(`\\*${targetLetter}([.\\)])`);
                    const wasSelected = wasSelectedRegex.test(targetLine);

                    if (!wasSelected) {
                        newLines[lineIdx] = newLines[lineIdx].replace(
                            new RegExp(`(^|\\s)(${targetLetter})([.\\)])`),
                            '$1*$2$3'
                        );
                    }
                }

                return { ...prev, raw_text: newLines.join('\n') };
            });
        },
        []
    );

    // --- 5. True/False Toggle Logic ---
    /**
     * Similar to MCQ, but toggles the asterisk (*) on/off without clearing siblings.
     */
    const handleTrueFalseToggle = useCallback(
        (
            _questionIndex: number,
            letter: string,
            _sourceLineNumber: number,
            answerLineNumber: number
        ) => {
            if (editorRef.current && answerLineNumber) {
                editorRef.current.scrollToLine(answerLineNumber);
            }

            setPreviewData((prev) => {
                if (!prev) return prev;
                const lines = prev.raw_text.split('\n');
                const lineIdx = answerLineNumber - 1;

                if (lineIdx >= 0 && lineIdx < lines.length) {
                    const line = lines[lineIdx];
                    const targetLetterLower = letter.toLowerCase();
                    const targetLetterUpper = letter.toUpperCase();

                    // Regex to find "A)", "a)", "*A)", or "*a)".
                    const regex = new RegExp(
                        `(\\*?)(${targetLetterLower}|${targetLetterUpper})([.)])`,
                        'gi'
                    );

                    if (regex.test(line)) {
                        const matchStar = line.match(
                            new RegExp(`\\*(${targetLetterLower}|${targetLetterUpper})[.)]`, 'i')
                        );
                        const hasStar = !!matchStar;

                        let newLine = line;
                        if (hasStar) {
                            // Turn OFF selection.
                            newLine = newLine.replace(
                                new RegExp(
                                    `\\*(${targetLetterLower}|${targetLetterUpper})([.)])`,
                                    'gi'
                                ),
                                '$1$2'
                            );
                        } else {
                            // Turn ON selection.
                            newLine = newLine.replace(
                                new RegExp(
                                    `(^|\\s)(${targetLetterLower}|${targetLetterUpper})([.)])`,
                                    'gi'
                                ),
                                '$1*$2$3'
                            );
                        }

                        if (newLine !== line) {
                            const newLines = [...lines];
                            newLines[lineIdx] = newLine;
                            return { ...prev, raw_text: newLines.join('\n') };
                        }
                    }
                }
                return prev;
            });
        },
        []
    );

    // --- 6. Short Answer Sync Logic ---
    /**
     * Updates the "Đáp án: [text]" line within the editor when a user 
     * types in the preview's short-answer input field.
     */
    const handleShortAnswerChange = useCallback(
        (questionIndex: number, text: string, sourceLineNumber: number) => {
            // STEP 1: Update the local memory map.
            setCorrectAnswers((prev) => {
                const newMap = new Map(prev);
                if (text) newMap.set(questionIndex, text);
                else newMap.delete(questionIndex);
                return newMap;
            });

            // STEP 2: Synchronize to the raw editor text.
            setPreviewData((prev) => {
                if (!prev) return prev;
                const lines = prev.raw_text.split('\n');

                if (!sourceLineNumber || sourceLineNumber < 1) return prev;
                const startIdx = sourceLineNumber - 1;

                // Find the end boundary of the current short-answer question.
                let endIdx = lines.length;
                const questionRegex = /(?:\[ID:[^\]]*\]\s*)?Câu\s*\d+/i;

                for (let i = startIdx + 1; i < lines.length; i++) {
                    const trimmed = lines[i].trim();
                    const upper = trimmed.toUpperCase();

                    // Stop at Section headers or the document end market.
                    if (
                        /^[-=\s]*HẾT[-=\s]*$/.test(upper) ||
                        upper === 'ĐÁP ÁN' ||
                        upper === 'BẢNG ĐÁP ÁN' ||
                        upper.includes('[!B:ĐÁP ÁN]')
                    ) {
                        endIdx = i;
                        break;
                    }

                    if (
                        trimmed.match(questionRegex) ||
                        trimmed.toLowerCase().includes('phần ii') ||
                        trimmed.toLowerCase().includes('phần iii')
                    ) {
                        endIdx = i;
                        break;
                    }
                }

                // Search for an existing 'Đáp án:' line within this block.
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
                    if (text) {
                        // Update existing line.
                        newLines[answerLineIdx] = `Đáp án: ${text}`;
                    } else {
                        // If text is cleared, remove the line.
                        newLines.splice(answerLineIdx, 1);
                    }
                } else {
                    if (text) {
                        // If no line exists, inject it at the end of the question block.
                        newLines.splice(endIdx, 0, `Đáp án: ${text}`);
                    }
                }

                return { ...prev, raw_text: newLines.join('\n') };
            });
        },
        []
    );

    // --- Reset Editor state ---
    const resetEditor = useCallback(() => {
        setPreviewData(null);
        setCorrectAnswers(new Map());
        setTrueFalseAnswers(new Map());
    }, []);

    return {
        previewData,
        correctAnswers,
        trueFalseAnswers,
        editorRef,
        isPreviewLoading: previewMutation.isPending,
        handleFilePreview,
        handleTextChange,
        handleLineClick,
        handleAnswerSelect,
        handleTrueFalseToggle,
        handleShortAnswerChange,
        resetEditor,
    };
}
