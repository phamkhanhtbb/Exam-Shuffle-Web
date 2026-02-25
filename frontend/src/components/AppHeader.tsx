import { X, RefreshCw, Play } from 'lucide-react';

/**
 * APP HEADER COMPONENT
 * 
 * The main control bar containing:
 * 1. Logo & Home navigation (Reset).
 * 2. Active file indicator.
 * 3. Configuration inputs (Number of variants, Exam codes).
 * 4. Primary action button (Start Shuffling).
 */

interface AppHeaderProps {
    fileName: string;
    numVariants: number;
    examCodes: string;
    isProcessing: boolean;
    onNumVariantsChange: (value: number) => void;
    onExamCodesChange: (value: string) => void;
    onReset: () => void;
    onSubmit: () => void;
}

const AppHeader: React.FC<AppHeaderProps> = ({
    fileName,
    numVariants,
    examCodes,
    isProcessing,
    onNumVariantsChange,
    onExamCodesChange,
    onReset,
    onSubmit,
}) => {
    return (
        <header className="app-header slide-down">
            {/* LEFT SECTION: Logo and File Information */}
            <div className="flex items-center gap-2 sm:gap-6 min-w-0">
                {/* Branding: Clickable to reset the app to the welcome screen. */}
                <div
                    className="logo cursor-pointer flex items-center gap-2 sm:gap-3 bg-gradient-to-r from-indigo-600 to-purple-600 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-xl shadow-lg hover:shadow-xl transition-shadow flex-shrink-0"
                    onClick={onReset}
                >
                    <span className="text-lg sm:text-xl">🎓</span>
                    <span className="hidden sm:inline text-lg font-bold text-white">ExamShuffling</span>
                </div>

                <div className="hidden sm:block h-8 w-px bg-gray-200"></div>

                {/* File Badge: Shows the currently uploaded DOCX filename. */}
                <div className="file-badge hidden sm:flex items-center gap-1">
                    <span className="text-gray-500 text-sm">File:</span>
                    <span className="font-medium text-indigo-700 max-w-[120px] sm:max-w-[200px] truncate" title={fileName}>
                        {fileName}
                    </span>
                    <button onClick={onReset} className="ml-1 text-gray-400 hover:text-red-500" title="Đóng file">
                        <X size={16} />
                    </button>
                </div>

                {/* Mobile version of the file badge (more compact). */}
                <div className="flex sm:hidden items-center gap-1 min-w-0">
                    <span className="font-medium text-indigo-700 text-xs truncate max-w-[100px]" title={fileName}>
                        {fileName}
                    </span>
                    <button onClick={onReset} className="text-gray-400 hover:text-red-500 flex-shrink-0">
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* RIGHT SECTION: Configuration & Primary Action */}
            <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
                {/* Variant Configuration: How many shuffled versions to generate. */}
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

                {/* Exam Codes: Optional comma-separated list of IDs for the variants (e.g. 101, 102). */}
                <div className="flex items-center gap-1.5 sm:gap-3 bg-gray-50 px-2 sm:px-4 py-1.5 sm:py-2 rounded-lg border border-gray-200">
                    <span className="hidden sm:inline text-sm font-medium text-gray-600">Mã đề:</span>
                    <span className="sm:hidden text-xs font-medium text-gray-600">MĐ:</span>
                    <input
                        type="text"
                        value={examCodes}
                        onChange={(e) => onExamCodesChange(e.target.value)}
                        placeholder="VD: 101,102,..."
                        className="w-24 sm:w-32 bg-transparent text-center font-bold text-indigo-600 outline-none border-b border-gray-300 focus:border-indigo-500 text-sm sm:text-base placeholder:text-gray-300 placeholder:font-normal placeholder:text-xs"
                    />
                </div>

                {/* Submit Action: Triggers the S3 upload and SQS job submission. */}
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
