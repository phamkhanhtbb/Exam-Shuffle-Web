import React from 'react';
import { Upload } from 'lucide-react';

interface WelcomeSectionProps {
    onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const WelcomeSection: React.FC<WelcomeSectionProps> = ({ onFileChange }) => {
    return (
        <div className="welcome-wrapper fade-in">
            {/* Main Card - Responsive sizing */}
            <div
                className="bg-white rounded-3xl shadow-2xl animate-scale-up overflow-hidden"
                style={{
                    width: 'min(90vw, 600px)',
                }}
            >
                {/* Logo Header inside card */}
                <div
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 flex flex-col items-center"
                    style={{ padding: 'clamp(16px, 2vw, 28px) clamp(20px, 3vw, 32px)' }}
                >
                    <h1
                        className="font-bold text-white tracking-wide flex items-center gap-2"
                        style={{ fontSize: 'clamp(18px, 1.8vw, 28px)' }}
                    >
                        🎓 ExamShuffling
                    </h1>
                    <p
                        className="text-indigo-100 font-light opacity-90 mt-1"
                        style={{ fontSize: 'clamp(11px, 1vw, 14px)' }}
                    >
                        Hệ thống tự động tạo đề thi trắc nghiệm
                    </p>
                </div>

                {/* Upload Zone */}
                <div style={{ padding: 'clamp(20px, 2.5vw, 32px)' }}>
                    <div
                        className="upload-zone border-2 border-dashed border-gray-200 rounded-2xl flex flex-col items-center justify-center relative group hover:border-indigo-400 hover:bg-indigo-50/30 transition-all cursor-pointer"
                        style={{ padding: 'clamp(28px, 3vw, 48px) clamp(16px, 2vw, 24px)' }}
                    >
                        <input
                            type="file"
                            accept=".docx"
                            onChange={onFileChange}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        />

                        <div
                            className="bg-gray-50 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300 border border-gray-100"
                            style={{ width: 'clamp(48px, 4vw, 64px)', height: 'clamp(48px, 4vw, 64px)' }}
                        >
                            <Upload
                                className="text-gray-400 group-hover:text-indigo-600 transition-colors"
                                style={{ width: 'clamp(20px, 1.8vw, 28px)', height: 'clamp(20px, 1.8vw, 28px)' }}
                            />
                        </div>

                        <h3
                            className="text-gray-800 font-semibold mb-1"
                            style={{ fontSize: 'clamp(14px, 1.2vw, 18px)' }}
                        >
                            Kéo thả file vào đây
                        </h3>
                        <p
                            className="text-gray-400 mb-3"
                            style={{ fontSize: 'clamp(11px, 0.9vw, 14px)' }}
                        >
                            hoặc
                        </p>

                        <button
                            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium shadow-md hover:from-indigo-700 hover:to-purple-700 transition-all"
                            style={{
                                padding: 'clamp(8px, 0.8vw, 12px) clamp(16px, 1.5vw, 24px)',
                                fontSize: 'clamp(12px, 1vw, 15px)'
                            }}
                        >
                            Chọn file từ máy tính
                        </button>

                        <p
                            className="text-gray-400 mt-3"
                            style={{ fontSize: 'clamp(10px, 0.8vw, 12px)' }}
                        >
                            Chỉ chấp nhận file .docx đã soạn
                        </p>
                    </div>

                    {/* Footer */}
                    <p
                        className="text-center text-gray-400 mt-4"
                        style={{ fontSize: 'clamp(9px, 0.7vw, 11px)' }}
                    >
                        Phát triển bởi <span className="font-medium">David Khanh👾</span> | Phiên bản Beta
                    </p>
                </div>
            </div>
        </div>
    );
};

export default WelcomeSection;
