import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Hook for drag-to-resize panel layout.
 * Returns the left panel width percentage, a container ref, and a mousedown handler.
 */
export function useResizablePanel(initialWidth = 60) {
    const [leftWidth, setLeftWidth] = useState(initialWidth);
    const [isResizing, setIsResizing] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const startResizing = useCallback(() => setIsResizing(true), []);
    const stopResizing = useCallback(() => setIsResizing(false), []);

    const resize = useCallback(
        (mouseMoveEvent: MouseEvent) => {
            if (isResizing && containerRef.current) {
                const containerRect = containerRef.current.getBoundingClientRect();
                let newWidth =
                    ((mouseMoveEvent.clientX - containerRect.left) / containerRect.width) * 100;
                if (newWidth < 20) newWidth = 20;
                if (newWidth > 80) newWidth = 80;
                setLeftWidth(newWidth);
            }
        },
        [isResizing]
    );

    useEffect(() => {
        window.addEventListener('mousemove', resize);
        window.addEventListener('mouseup', stopResizing);
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [resize, stopResizing]);

    return { leftWidth, containerRef, startResizing };
}
