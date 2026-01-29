import React from 'react';
import { GripVertical } from 'lucide-react';

interface PaneResizerProps {
    onMouseDown: () => void;
}

const PaneResizer: React.FC<PaneResizerProps> = ({ onMouseDown }) => {
    return (
        <div
            className="w-1.5 bg-gray-300 hover:bg-indigo-500 cursor-col-resize flex items-center justify-center transition-colors z-50 hover:shadow-lg active:bg-indigo-600"
            onMouseDown={onMouseDown}
        >
            <GripVertical size={12} className="text-gray-400" />
        </div>
    );
};

export default PaneResizer;
