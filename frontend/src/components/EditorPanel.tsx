import React, { useRef } from 'react';
import { Code, Edit3 } from 'lucide-react';

/**
 * EDITOR PANEL COMPONENT
 * 
 * Provides a high-performance text editor with real-time syntax highlighting.
 * It uses a dual-layer approach:
 * 1. BACK LAYER: A static <div> that renders highlighted HTML (Regex-based).
 * 2. FRONT LAYER: A transparent <textarea> for user input.
 */

export interface EditorPanelHandle {
    scrollToLine: (lineNumber: number) => void;
}

interface EditorPanelProps {
    width: number;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    isMobile?: boolean;
}

/**
 * Perform regex-based syntax highlighting for the back layer.
 * Targets: Questions, Answers, Math markers, and Image placeholders.
 */
const highlightSyntax = (text: string): string => {
    // Escape HTML characters to prevent XSS and rendering breakages.
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Highlight: 'Câu 1', 'Câu 2', etc. (Indigo/Bold)
    html = html.replace(
        /(Câu\s*\d+[:.]*)/gi,
        '<span class="text-indigo-600 font-bold">$1</span>'
    );

    // Highlight: Answers markers 'A.', 'B.', and marked answers '*A.' (Red/Bold)
    html = html.replace(
        /((?<![0-9])\s|^)(\*?[A-D][.)])/gim,
        '$1<span class="text-red-500 font-bold">$2</span>'
    );

    // Highlight: Math formula IDs '[!m:ID$]' (Fuchsia)
    html = html.replace(
        /(\[!m:[^\]]+\$\])/gi,
        '<span class="text-fuchsia-600 bg-fuchsia-50 font-bold">$1</span>'
    );

    // Highlight: Image IDs '[img:ID$]' (Amber)
    html = html.replace(
        /(\[img:[^\]]+\$\])/gi,
        '<span class="text-amber-600 bg-amber-50 font-bold">$1</span>'
    );

    // Highlight: System metadata IDs '[ID:hash]' (Grayed out)
    html = html.replace(
        /(\[ID:[a-fA-F0-9]{8,}\])/g,
        '<span class="text-gray-400 opacity-60">$1</span>'
    );

    // TRICK: HTML ignores trailing newlines in <div>, so we manually add a break
    // to keep the background height synchronized with the textarea.
    if (text.endsWith('\n')) {
        html += '<br />';
    }

    return html;
};

const EditorPanel = React.forwardRef<EditorPanelHandle, EditorPanelProps>(({ width, value, onChange, isMobile }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const highlightRef = useRef<HTMLDivElement>(null);

    // Expose a 'scrollToLine' method to the parent (App.tsx).
    React.useImperativeHandle(ref, () => ({
        scrollToLine: (lineNumber: number) => {
            if (textareaRef.current) {
                // Calculate pixel offset based on line height.
                const fontSize = isMobile ? 12 : 14;
                const lineHeight = fontSize * 1.5;
                const scrollTop = (lineNumber - 1) * lineHeight;

                textareaRef.current.scrollTo({
                    top: scrollTop,
                    behavior: 'smooth'
                });

                if (document.activeElement !== textareaRef.current) {
                    textareaRef.current.focus({ preventScroll: true });
                }
            }
        }
    }));

    // CRITICAL: Synchronize the scroll position of the highlight layer with the textarea.
    const handleScroll = () => {
        if (textareaRef.current && highlightRef.current) {
            highlightRef.current.scrollTop = textareaRef.current.scrollTop;
            highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
        }
    };

    // Shared styles to ensure perfect alignment between the two layers.
    const sharedStyle: React.CSSProperties = {
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        fontSize: isMobile ? '12px' : '14px',
        lineHeight: '1.5',
        letterSpacing: '0px',
        padding: '16px',
        whiteSpace: 'pre-wrap',
        wordWrap: 'break-word',
        overflowWrap: 'break-word',
        overflowY: 'scroll',
        overflowX: 'hidden',
        boxSizing: 'border-box',
        margin: 0,
        border: 'none',
    };

    return (
        <div
            className="flex flex-col bg-gray-50 border-l border-gray-200 min-w-0 shadow-lg z-20 transition-none h-full"
            style={{ width: isMobile ? '100%' : `${width}%` }}
        >
            {/* Header Toolbar */}
            <div className={`${isMobile ? 'h-9 px-3' : 'h-11 px-4'} border-b border-gray-200 bg-white flex items-center justify-between shrink-0`}>
                <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                    <Code size={isMobile ? 12 : 14} className="text-indigo-500" /> Mã nguồn
                </span>
                <span className="text-[10px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1 font-medium">
                    <Edit3 size={isMobile ? 8 : 10} /> Edit
                </span>
            </div>

            {/* Main Interactive Editor Area */}
            <div className="flex-1 relative bg-white">
                {/* 1. Syntax highlight layer (Hidden from interaction) */}
                <div
                    ref={highlightRef}
                    className="absolute inset-0 pointer-events-none text-gray-800"
                    style={sharedStyle}
                    dangerouslySetInnerHTML={{ __html: highlightSyntax(value) || '<span class="text-gray-400">Mã nguồn đề thi sẽ hiện ở đây...</span>' }}
                />

                {/* 2. Transparent textarea (Handles all keyboard/mouse events) */}
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
