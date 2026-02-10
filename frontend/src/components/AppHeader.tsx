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
            <div className="flex items-center gap-2 sm:gap-6 min-w-0">
                {/* Logo - compact on mobile */}
                <div
                    className="logo cursor-pointer flex items-center gap-2 sm:gap-3 bg-gradient-to-r from-indigo-600 to-purple-600 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-xl shadow-lg hover:shadow-xl transition-shadow flex-shrink-0"
                    onClick={onReset}
                >
                    <span className="text-lg sm:text-xl">🎓</span>
                    <span className="hidden sm:inline text-lg font-bold text-white">ExamShuffling</span>
                </div>

                {/* Divider - hidden on mobile */}
                <div className="hidden sm:block h-8 w-px bg-gray-200"></div>

                {/* File badge - truncated on mobile */}
                <div className="file-badge hidden sm:flex items-center gap-1">
                    <span className="text-gray-500 text-sm">File:</span>
                    <span className="font-medium text-indigo-700 max-w-[120px] sm:max-w-[200px] truncate" title={fileName}>
                        {fileName}
                    </span>
                    <button onClick={onReset} className="ml-1 text-gray-400 hover:text-red-500">
                        <X size={16} />
                    </button>
                </div>

                {/* Mobile-only: file name short */}
                <div className="flex sm:hidden items-center gap-1 min-w-0">
                    <span className="font-medium text-indigo-700 text-xs truncate max-w-[100px]" title={fileName}>
                        {fileName}
                    </span>
                    <button onClick={onReset} className="text-gray-400 hover:text-red-500 flex-shrink-0">
                        <X size={14} />
                    </button>
                </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
                {/* Variant count */}
                <div className="flex items-center gap-1.5 sm:gap-3 bg-gray-50 px-2 sm:px-4 py-1.5 sm:py-2 rounded-lg border border-gray-200">
                    <span className="hidden sm:inline text-sm font-medium text-gray-600">Số lượng đề:</span>
                    <span className="sm:hidden text-xs font-medium text-gray-600">SL:</span>
                    <input
                        type="number"
                        min="1"
                        max="100"
                        value={numVariants}
                        onChange={(e) => onNumVariantsChange(parseInt(e.target.value))}
                        className="w-10 sm:w-12 bg-transparent text-center font-bold text-indigo-600 outline-none border-b border-gray-300 focus:border-indigo-500 text-sm sm:text-base"
                    />
                </div>

                {/* Submit button */}
                <button
                    onClick={onSubmit}
                    disabled={isProcessing}
                    className={`btn-action text-white shadow-lg shadow-purple-200 ${isProcessing ? 'bg-gray-400' : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700'
                        }`}
                >
                    {isProcessing ? (
                        <RefreshCw className="animate-spin" size={18} />
                    ) : (
                        <Play size={18} fill="currentColor" />
                    )}
                    <span className="hidden sm:inline">{isProcessing ? 'Đang xử lý...' : 'Bắt đầu Trộn'}</span>
                    <span className="sm:hidden">{isProcessing ? '...' : 'Trộn'}</span>
                </button>
            </div>
        </header>
    );
};

export default AppHeader;
