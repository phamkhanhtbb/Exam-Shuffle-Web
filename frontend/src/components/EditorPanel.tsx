import React, { useRef } from 'react';
import { Code, Edit3 } from 'lucide-react';

export interface EditorPanelHandle {
    scrollToLine: (lineNumber: number) => void;
}

interface EditorPanelProps {
    width: number;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

// Highlight function for syntax coloring
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

    // A., B., C., D. (and *A., a., etc.) answers - Red
    // Match start of line OR whitespace preceding, then optional *, then letter, then dot or paren
    html = html.replace(
        /(\s|^)(\*?[A-D][\.\)])/gim,
        '$1<span class="text-red-500 font-bold">$2</span>'
    );

    // [!m:ID$] - Mathtype - Fuchsia (High Contrast)
    // REMOVED padding/border to ensure perfect alignment with textarea
    html = html.replace(
        /(\[!m:[^\]]+\$\])/gi,
        '<span class="text-fuchsia-600 bg-fuchsia-50 font-bold">$1</span>'
    );

    // [img:ID$] - Images - Amber/Gold (Distinct)
    html = html.replace(
        /(\[img:[^\]]+\$\])/gi,
        '<span class="text-amber-600 bg-amber-50 font-bold">$1</span>'
    );

    // [table:ID$] - Tables - Blue (Deep)
    html = html.replace(
        /(\[table:[^\]]+\])/gi,
        '<span class="text-blue-700 bg-blue-50 font-bold">$1</span>'
    );

    // Catch-all for other brackets like [* ... *] for tables
    html = html.replace(
        /(\[\*\s.*?\s\*\])/gi,
        '<span class="text-blue-700 bg-blue-50 font-bold">$1</span>'
    );

    // Fix trailing newline issue: HTML ignores the last \n, causing a 1-line mismatch
    if (text.endsWith('\n')) {
        html += '<br />';
    }

    return html;
};

const EditorPanel = React.forwardRef<EditorPanelHandle, EditorPanelProps>(({ width, value, onChange }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const highlightRef = useRef<HTMLDivElement>(null);

    React.useImperativeHandle(ref, () => ({
        scrollToLine: (lineNumber: number) => {
            if (textareaRef.current) {
                // Line height is 1.5 * 14px = 21px
                const lineHeight = 21;
                const scrollTop = (lineNumber - 1) * lineHeight;

                // Use smooth scrolling
                textareaRef.current.scrollTo({
                    top: scrollTop,
                    behavior: 'smooth'
                });
                // Also focus logic? Focus might jump, so maybe just focus without scroll?
                // Actually, if we focus, browser might auto-scroll.
                // Let's keep focus but rely on scrollTo for positioning.
                if (document.activeElement !== textareaRef.current) {
                    textareaRef.current.focus({ preventScroll: true });
                }
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

    const sharedStyle: React.CSSProperties = {
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        fontSize: '14px',
        lineHeight: '1.5',

        letterSpacing: '0px',
        padding: '16px',
        whiteSpace: 'pre-wrap',       // Enable wrapping for readability
        wordWrap: 'break-word',       // Ensure long words break
        overflowWrap: 'break-word',   // Modern standard
        overflowY: 'scroll',          // Force scrollbar on both
        overflowX: 'hidden',          // Hide horizontal scroll (handled by wrap)
        boxSizing: 'border-box',      // Include padding/border in size
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
            <div className="flex-1 relative bg-white">
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
                    spellCheck={false}
                    placeholder=""
                />
            </div>
        </div>
    );
});

EditorPanel.displayName = 'EditorPanel';

export default EditorPanel;
