import React from 'react';
import { FileText, Loader2 } from 'lucide-react';
import PreviewRenderer, { AssetMap } from './PreviewRenderer';

interface PreviewPanelProps {
    width: number;
    isLoading: boolean;
    previewData: { raw_text: string; assets_map: AssetMap } | null;
    onLineClick?: (lineNumber: number) => void;
    onAnswerSelect?: (questionIndex: number, answer: string, sourceLineNumber: number, answerLineNumber: number) => void;
    correctAnswers?: Map<number, string>;
    trueFalseAnswers?: Map<string, boolean>;
    onTrueFalseToggle?: (questionIndex: number, letter: string, sourceLineNumber: number, answerLineNumber: number) => void;
    onShortAnswerChange?: (questionIndex: number, text: string) => void;
}

const PreviewPanel: React.FC<PreviewPanelProps> = ({
    width, isLoading, previewData,
    onLineClick, onAnswerSelect, correctAnswers, trueFalseAnswers, onTrueFalseToggle, onShortAnswerChange
}) => {
    return (
        <div
            className="flex flex-col border-r border-gray-200 bg-gray-50/50 min-w-0 transition-none"
            style={{ width: `${width}%` }}
        >
            <div className="h-10 border-b border-gray-200 bg-white flex items-center justify-between px-4 shrink-0 shadow-sm z-10">
                <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                    <FileText size={14} /> Giao diện Đề thi
                </span>
                <span className="text-[10px] font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded border border-green-200 uppercase">
                    Live Preview
                </span>
            </div>
            <div className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
                {isLoading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-20 backdrop-blur-sm">
                        <Loader2 className="animate-spin text-indigo-600 mb-3" size={32} />
                        <p className="text-gray-600 font-medium animate-pulse">Đang phân tích cấu trúc...</p>
                    </div>
                )}
                {previewData && (
                    <div className="max-w-[21cm] mx-auto bg-white min-h-[29.7cm] shadow-lg border border-gray-200 p-10 transition-all origin-top animate-fade-in-up preview-paper">
                        <PreviewRenderer
                            rawText={previewData.raw_text}
                            assetsMap={previewData.assets_map}
                            onLineClick={onLineClick}
                            onAnswerSelect={onAnswerSelect}
                            correctAnswers={correctAnswers}
                            trueFalseAnswers={trueFalseAnswers}
                            onTrueFalseToggle={onTrueFalseToggle}
                            onShortAnswerChange={onShortAnswerChange}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};

export default PreviewPanel;
