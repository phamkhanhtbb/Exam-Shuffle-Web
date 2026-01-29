import React from 'react';
import { X, RefreshCw, Play } from 'lucide-react';

interface AppHeaderProps {
    fileName: string;
    numVariants: number;
    isProcessing: boolean;
    onNumVariantsChange: (value: number) => void;
    onReset: () => void;
    onSubmit: () => void;
}

const AppHeader: React.FC<AppHeaderProps> = ({
    fileName,
    numVariants,
    isProcessing,
    onNumVariantsChange,
    onReset,
    onSubmit,
}) => {
    return (
        <header className="app-header slide-down">
            <div className="flex items-center gap-6">
                {/* Logo matching Welcome section */}
                <div
                    className="logo cursor-pointer flex items-center gap-3 bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 rounded-xl shadow-lg hover:shadow-xl transition-shadow"
                    onClick={onReset}
                >
                    <span className="text-xl">🎓</span>
                    <span className="text-lg font-bold text-white">ExamShuffling</span>
                </div>
                <div className="h-8 w-px bg-gray-200"></div>
                <div className="file-badge">
                    <span className="text-gray-500 text-sm">File:</span>
                    <span className="font-medium text-indigo-700 max-w-[200px] truncate" title={fileName}>
                        {fileName}
                    </span>
                    <button onClick={onReset} className="ml-2 text-gray-400 hover:text-red-500">
                        <X size={16} />
                    </button>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 rounded-lg border border-gray-200">
                    <span className="text-sm font-medium text-gray-600">Số lượng đề:</span>
                    <input
                        type="number"
                        min="1"
                        max="100"
                        value={numVariants}
                        onChange={(e) => onNumVariantsChange(parseInt(e.target.value))}
                        className="w-12 bg-transparent text-center font-bold text-indigo-600 outline-none border-b border-gray-300 focus:border-indigo-500"
                    />
                </div>

                <button
                    onClick={onSubmit}
                    disabled={isProcessing}
                    className={`btn-action text-white shadow-lg shadow-purple-200 ${isProcessing ? 'bg-gray-400' : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700'
                        }`}
                >
                    {isProcessing ? (
                        <RefreshCw className="animate-spin" size={20} />
                    ) : (
                        <Play size={20} fill="currentColor" />
                    )}
                    {isProcessing ? 'Đang xử lý...' : 'Bắt đầu Trộn'}
                </button>
            </div>
        </header>
    );
};

export default AppHeader;
