import React, { useState } from 'react';
import { FileText, Code } from 'lucide-react';
import PreviewPanel from './PreviewPanel';
import EditorPanel, { EditorPanelHandle } from './EditorPanel';
import PaneResizer from './PaneResizer';
import type { PreviewData } from '../hooks/useExamEditor';

/**
 * Workspace Component.
 * The central container for the two main interaction areas: 
 * the interactive Preview and the raw Text Editor.
 * 
 * Features:
 * - Desktop: Side-by-side view with a draggable resizer.
 * - Mobile: Tabbed view to switch between Preview and Editor.
 */

interface WorkspaceProps {
    previewData: PreviewData | null;
    isPreviewLoading: boolean;
    editorRef: React.RefObject<EditorPanelHandle>;
    isMobile: boolean;
    leftWidth: number;                  // Width (%) of the left panel (Preview).
    containerRef: React.RefObject<HTMLDivElement>;
    startResizing: () => void;
    correctAnswers: Map<number, string>;
    trueFalseAnswers: Map<string, boolean>;
    onLineClick: (lineNumber: number) => void;
    onAnswerSelect: (
        questionIndex: number,
        answer: string,
        sourceLineNumber: number,
        answerLineNumber: number
    ) => void;
    onTrueFalseToggle: (
        questionIndex: number,
        letter: string,
        sourceLineNumber: number,
        answerLineNumber: number
    ) => void;
    onShortAnswerChange: (
        questionIndex: number,
        text: string,
        sourceLineNumber: number
    ) => void;
    onTextChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

const Workspace: React.FC<WorkspaceProps> = ({
    previewData,
    isPreviewLoading,
    editorRef,
    isMobile,
    leftWidth,
    containerRef,
    startResizing,
    correctAnswers,
    trueFalseAnswers,
    onLineClick,
    onAnswerSelect,
    onTrueFalseToggle,
    onShortAnswerChange,
    onTextChange,
}) => {
    // Local state to track the active view on mobile devices.
    const [activeTab, setActiveTab] = useState<'preview' | 'editor'>('preview');

    return (
        <div
            className="workspace-wrapper flex w-full h-full bg-gray-100 overflow-hidden animate-expand"
            ref={containerRef}
        >
            {/* 1. Mobile Tab Navigation (Hidden on Desktop) */}
            {isMobile && (
                <div className="mobile-tab-bar">
                    <button
                        className={activeTab === 'preview' ? 'active' : ''}
                        onClick={() => setActiveTab('preview')}
                    >
                        <FileText size={16} /> Preview
                    </button>
                    <button
                        className={activeTab === 'editor' ? 'active' : ''}
                        onClick={() => setActiveTab('editor')}
                    >
                        <Code size={16} /> Editor
                    </button>
                </div>
            )}

            {/* 2. Left Panel: Interactive Preview of the Exam. */}
            {(!isMobile || activeTab === 'preview') && (
                <PreviewPanel
                    width={leftWidth}
                    isLoading={isPreviewLoading}
                    previewData={previewData}
                    onLineClick={onLineClick}
                    onAnswerSelect={onAnswerSelect}
                    correctAnswers={correctAnswers}
                    onTrueFalseToggle={onTrueFalseToggle}
                    trueFalseAnswers={trueFalseAnswers}
                    onShortAnswerChange={onShortAnswerChange}
                    isMobile={isMobile}
                />
            )}

            {/* 3. Central Divider: Draggable handle to resize panels (Desktop only). */}
            {!isMobile && <PaneResizer onMouseDown={startResizing} />}

            {/* 4. Right Panel: Raw Text Editor for manual corrections. */}
            {(!isMobile || activeTab === 'editor') && (
                <EditorPanel
                    ref={editorRef}
                    width={100 - leftWidth}
                    value={previewData?.raw_text || ''}
                    onChange={onTextChange}
                    isMobile={isMobile}
                />
            )}
        </div>
    );
};

export default Workspace;
