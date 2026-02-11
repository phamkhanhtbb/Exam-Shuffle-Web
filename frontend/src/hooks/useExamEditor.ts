import { useCallback, useRef, useState } from 'react';
import { AssetMap } from '../components/PreviewRenderer';
import { EditorPanelHandle } from '../components/EditorPanel';
import { usePreviewExam } from './useExamApi';

export interface PreviewData {
    raw_text: string;
    assets_map: AssetMap;
    question_count: number;
}

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
 * Custom hook encapsulating all bidirectional editor logic:
 * preview data, answer selection, true/false toggling, short answer editing.
 */
export function useExamEditor(): ExamEditorActions {
    const [previewData, setPreviewData] = useState<PreviewData | null>(null);
    const [correctAnswers, setCorrectAnswers] = useState<Map<number, string>>(new Map());
    const [trueFalseAnswers, setTrueFalseAnswers] = useState<Map<string, boolean>>(new Map());
    const editorRef = useRef<EditorPanelHandle>(null);

    const previewMutation = usePreviewExam();

    // --- File Preview ---
    const handleFilePreview = useCallback(async (file: File) => {
        const result = await previewMutation.mutateAsync(file);
        if (result.status === 'success') {
            setPreviewData(result.data);

            // Initialize correctAnswers from raw text (for short answer questions)
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

    // --- Text Change ---
    const handleTextChange = useCallback(
        (e: React.ChangeEvent<HTMLTextAreaElement>) => {
            setPreviewData((prev) => {
                if (!prev) return prev;
                return { ...prev, raw_text: e.target.value };
            });
        },
        []
    );

    // --- Line Click (scroll editor) ---
    const handleLineClick = useCallback((lineNumber: number) => {
        if (editorRef.current) {
            editorRef.current.scrollToLine(lineNumber);
        }
    }, []);

    // --- MCQ Answer Select (bidirectional) ---
    const handleAnswerSelect = useCallback(
        (
            _questionIndex: number,
            answer: string,
            sourceLineNumber: number,
            answerLineNumber: number
        ) => {
            if (editorRef.current && answerLineNumber) {
                editorRef.current.scrollToLine(answerLineNumber);
            }

            setPreviewData((prev) => {
                if (!prev) return prev;

                const lines = prev.raw_text.split('\n');
                const startIdx = sourceLineNumber - 1;

                // Search boundaries: from startIdx until next "Câu" or Part header
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

                // Clear existing * from ALL options (A-H) in this range
                const newLines = [...lines];
                for (let j = startIdx; j < endIdx; j++) {
                    newLines[j] = newLines[j].replace(/(\*)([A-H])([.\\)])/g, '$2$3');
                }

                // Set the new answer using answerLineNumber directly
                if (answerLineNumber && answerLineNumber > 0 && answerLineNumber <= lines.length) {
                    const lineIdx = answerLineNumber - 1;
                    const targetLine = lines[lineIdx]; // Use ORIGINAL line to check state
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

    // --- True/False Toggle (bidirectional) ---
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
                            newLine = newLine.replace(
                                new RegExp(
                                    `\\*(${targetLetterLower}|${targetLetterUpper})([.)])`,
                                    'gi'
                                ),
                                '$1$2'
                            );
                        } else {
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

    // --- Short Answer Change (bidirectional) ---
    const handleShortAnswerChange = useCallback(
        (questionIndex: number, text: string, sourceLineNumber: number) => {
            // 1. Update Correct Answers Map
            setCorrectAnswers((prev) => {
                const newMap = new Map(prev);
                if (text) newMap.set(questionIndex, text);
                else newMap.delete(questionIndex);
                return newMap;
            });

            // 2. Update Raw Text (Bidirectional Sync)
            setPreviewData((prev) => {
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
                        trimmed.toLowerCase().includes('phần 2') ||
                        trimmed.toLowerCase().includes('phần iii') ||
                        trimmed.toLowerCase().includes('phần 3')
                    ) {
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
                    if (text) {
                        newLines[answerLineIdx] = `Đáp án: ${text}`;
                    } else {
                        newLines.splice(answerLineIdx, 1);
                    }
                } else {
                    if (text) {
                        newLines.splice(endIdx, 0, `Đáp án: ${text}`);
                    }
                }

                return { ...prev, raw_text: newLines.join('\n') };
            });
        },
        []
    );

    // --- Reset ---
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
