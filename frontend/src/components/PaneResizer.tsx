import React from 'react';
import { GripVertical } from 'lucide-react';

/**
 * PANE RESIZER COMPONENT
 * 
 * A vertical divider used in Desktop mode to allow users to 
 * manually adjust the width of the Preview vs. Editor panels.
 */

interface PaneResizerProps {
    onMouseDown: () => void;
}

const PaneResizer: React.FC<PaneResizerProps> = ({ onMouseDown }) => {
    return (
        <div
            className="pane-resizer-desktop w-1.5 bg-gray-300 hover:bg-indigo-500 cursor-col-resize flex items-center justify-center transition-colors z-50 hover:shadow-lg active:bg-indigo-600"
            // Triggers the mouse tracking logic in useResizablePanel.ts
            onMouseDown={onMouseDown}
            // Mobile equivalent for resizing (though rarely used on small screens).
            onTouchStart={onMouseDown}
        >
            {/* Visual handle icon. */}
            <GripVertical size={12} className="text-gray-400" />
        </div>
    );
};

export default PaneResizer;
