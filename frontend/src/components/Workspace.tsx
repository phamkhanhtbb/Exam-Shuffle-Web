import React, { useState } from 'react';
import { FileText, Code } from 'lucide-react';
import PreviewPanel from './PreviewPanel';
import EditorPanel, { EditorPanelHandle } from './EditorPanel';
import PaneResizer from './PaneResizer';
import type { PreviewData } from '../hooks/useExamEditor';

interface WorkspaceProps {
    previewData: PreviewData | null;
    isPreviewLoading: boolean;
    editorRef: React.RefObject<EditorPanelHandle>;
    isMobile: boolean;
    leftWidth: number;
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

/**
 * Workspace layout — manages mobile tab bar and renders
 * PreviewPanel + PaneResizer + EditorPanel side by side.
 */
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
    const [activeTab, setActiveTab] = useState<'preview' | 'editor'>('preview');

    return (
        <div
            className="workspace-wrapper flex w-full h-full bg-gray-100 overflow-hidden animate-expand"
            ref={containerRef}
        >
            {/* Mobile Tab Bar */}
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

            {/* Preview Panel */}
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

            {/* Resizer: desktop only */}
            {!isMobile && <PaneResizer onMouseDown={startResizing} />}

            {/* Editor Panel */}
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
