import React, { useRef, forwardRef, useImperativeHandle, useState } from 'react';
import { Code, Edit3 } from 'lucide-react';

interface EditorPanelProps {
    width: number;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    assetsMap?: Record<string, any>;
    onAssetUpdate?: (id: string, newLatex: string) => void;
}

// Expose scrollToLine method via ref
export interface EditorPanelHandle {
    scrollToLine: (lineNumber: number) => void;
}

const highlightSyntax = (text: string): string => {
    // Escape HTML
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Câu 1, Câu 2, etc. - Purple (indigo)
    html = html.replace(
        /(Câu\s*\d+[\.:]*)/gi,
        '<span class="text-indigo-600 font-bold">$1</span>'
    );

    // Correct answers with * prefix (*A., *B., *C., *D.) - Green
    html = html.replace(
        /^(\s*)(\*[A-Da-d]\.)/gm,
        '$1<span class="text-green-600 bg-green-50 font-bold">$2</span>'
    );

    // Regular A., B., C., D. answers - Red
    html = html.replace(
        /^(\s*)([A-Da-d]\.)/gm,
        '$1<span class="text-red-500 font-bold">$2</span>'
    );

    // [!m:ID$] - Mathtype - Fuchsia (High Contrast)
    html = html.replace(
        /(\[!m:[^\]]+\$\])/gi,
        '<span class="text-fuchsia-600 bg-fuchsia-50 font-bold border-b-2 border-fuchsia-200 cursor-pointer" title="Click to edit math">$1</span>'
    );

    // [img:ID$] - Images - Amber/Gold (Distinct)
    html = html.replace(
        /(\[img:[^\]]+\$\])/gi,
        '<span class="text-amber-600 bg-amber-50 font-bold">$1</span>'
    );

    // Fix trailing newline issue: HTML ignores the last \n
    if (text.endsWith('\n')) {
        html += '<br />';
    }

    return html;
};

const EditorPanel = forwardRef<EditorPanelHandle, EditorPanelProps>(({ width, value, onChange, assetsMap, onAssetUpdate }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const highlightRef = useRef<HTMLDivElement>(null);

    // Popup state
    const [activeMathId, setActiveMathId] = useState<string | null>(null);
    const [popupPos, setPopupPos] = useState({ top: 0, left: 0 });
    const [editLatex, setEditLatex] = useState('');

    // Expose scrollToLine method to parent via ref
    useImperativeHandle(ref, () => ({
        scrollToLine: (lineNumber: number) => {
            if (textareaRef.current) {
                const textarea = textareaRef.current;
                const lineHeight = 21;
                const scrollTop = (lineNumber - 1) * lineHeight;

                textarea.scrollTop = scrollTop;
                // Also sync highlight layer
                if (highlightRef.current) {
                    highlightRef.current.scrollTop = scrollTop;
                }

                // Focus and set cursor to that line
                const lines = value.split('\n');
                let charIndex = 0;
                for (let i = 0; i < lineNumber - 1 && i < lines.length; i++) {
                    charIndex += lines[i].length + 1; // +1 for newline
                }
                textarea.focus();
                textarea.setSelectionRange(charIndex, charIndex);
            }
        }
    }));

    // Sync scroll between textarea and highlight overlay
    const handleScroll = () => {
        if (textareaRef.current && highlightRef.current) {
            highlightRef.current.scrollTop = textareaRef.current.scrollTop;
            highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
        }
    };

    // Handle click to detect math placeholder
    const handleClick = () => {
        if (!assetsMap || !textareaRef.current) return;

        const cursor = textareaRef.current.selectionStart;

        // Find all math placeholders
        const regex = /\[!m:([^$]+)\$\]/g;
        let match;
        let foundId = null;

        while ((match = regex.exec(value)) !== null) {
            const start = match.index;
            const end = start + match[0].length;

            // Check if cursor is inside this placeholder
            if (cursor >= start && cursor <= end) {
                foundId = match[1]; // mathtype_N match

                // Calculate position for popup
                // Simple approximation: line number * line height
                const beforeText = value.substring(0, start);
                const lines = beforeText.split('\n');
                const lineNum = lines.length; // 1-based rough line count

                // Fine-tune top position relative to scroll
                // We need to account for scrollTop if popup is relative to container, 
                // but if container is overflow-y-auto, absolute child moves with scroll?
                // Textarea and Highlight are in 'relative' container.
                // Scroll is on the textarea itself? No, styles say "overflowY: scroll".
                // Popup should be outside validity of overflow?

                // If popup is inside the scrollable area, it moves with text. Good.
                const top = (lineNum) * 21;

                // Approximate left
                const lastLine = lines[lines.length - 1];
                const left = Math.min(lastLine.length * 8.5 + 20, 600);

                setPopupPos({ top, left });
                break;
            }
        }

        if (foundId) {
            setActiveMathId(foundId);
            setEditLatex(assetsMap[foundId]?.latex || '');
        } else {
            // Only dismiss if not clicking inside popup (handled by z-index/propagation usually, but this is textarea click)
            setActiveMathId(null);
        }
    };

    const handleSaveMath = () => {
        if (activeMathId && onAssetUpdate) {
            onAssetUpdate(activeMathId, editLatex);
            setActiveMathId(null);
        }
    };

    const sharedStyle: React.CSSProperties = {
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        fontSize: '14px',
        lineHeight: '1.5',
        letterSpacing: '0px',
        padding: '16px',
        whiteSpace: 'pre-wrap',
        wordWrap: 'break-word',
        overflowWrap: 'break-word',
        overflowY: 'scroll',
        boxSizing: 'border-box',
        margin: 0,
        border: 'none',
    };

    return (
        <div
            className="flex flex-col bg-gray-50 border-l border-gray-200 min-w-0 shadow-lg z-20 transition-none"
            style={{ width: `${width}%` }}
        >
            {/* Header */}
            <div className="h-11 border-b border-gray-200 bg-white flex items-center justify-between px-4 shrink-0">
                <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                    <Code size={14} className="text-indigo-500" /> Mã nguồn (Editor)
                </span>
                <span className="text-[10px] text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200 flex items-center gap-1 font-medium">
                    <Edit3 size={10} /> Editable
                </span>
            </div>

            {/* Editor with syntax highlighting */}
            <div className="flex-1 relative bg-white overflow-hidden">
                {/* Syntax highlight layer (behind) */}
                <div
                    ref={highlightRef}
                    className="absolute inset-0 pointer-events-none text-gray-800"
                    style={sharedStyle}
                    dangerouslySetInnerHTML={{ __html: highlightSyntax(value) || '<span class="text-gray-400">Mã nguồn đề thi sẽ hiện ở đây...</span>' }}
                />

                {/* Transparent textarea (front, for editing) */}
                <textarea
                    ref={textareaRef}
                    className="w-full h-full bg-transparent text-transparent caret-gray-800 outline-none focus:bg-indigo-50/10 transition-colors z-10 relative block"
                    style={sharedStyle}
                    value={value}
                    onChange={onChange}
                    onScroll={handleScroll}
                    onClick={handleClick}
                    spellCheck={false}
                    placeholder=""
                />

                {/* Math Editor Popup */}
                {activeMathId && (
                    <div
                        className="absolute z-50 bg-white shadow-xl border border-indigo-200 rounded-lg p-3 w-96 animate-fade-in"
                        style={{ top: popupPos.top, left: popupPos.left }}
                    >
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded uppercase flex items-center gap-1">
                                <span>Math ID:</span> {activeMathId}
                            </span>
                            <button
                                onClick={(e) => { e.stopPropagation(); setActiveMathId(null); }}
                                className="text-gray-400 hover:text-red-500 font-bold px-1"
                            >
                                ×
                            </button>
                        </div>
                        <div className="text-[10px] text-gray-500 mb-1">LaTeX Source:</div>
                        <textarea
                            className="w-full h-24 p-2 text-sm border border-gray-300 rounded focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none font-mono mb-2 text-gray-800"
                            value={editLatex}
                            onChange={(e) => setEditLatex(e.target.value)}
                            placeholder="\frac{...}{...}"
                            autoFocus
                        />
                        <div className="flex justify-end gap-2">
                            <button
                                onClick={handleSaveMath}
                                className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-bold rounded hover:bg-indigo-700 transition shadow-sm"
                            >
                                Lưu thay đổi
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
});

EditorPanel.displayName = 'EditorPanel';

export default EditorPanel;
