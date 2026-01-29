// // // import React, { useState } from 'react';
// // // import { FileUpload } from './components/FileUpload';
// // // import { ProgressTracker } from './components/ProgressTracker';
// // // import { ExamShufflingService } from './services/examShufflingService';
// // // import { UploadJob, JobStatus, UploadProgress, JobStatusResponse } from './types';
// // // import { Download, RefreshCw } from 'lucide-react';
// // // import './App.css';
// // //
// // // function App() {
// // //   const [selectedFile, setSelectedFile] = useState<File | null>(null);
// // //   const [numVariants, setNumVariants] = useState<number>(10);
// // //   const [isProcessing, setIsProcessing] = useState(false);
// // //   const [uploadProgress, setUploadProgress] = useState<number>(0);
// // //   const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
// // //   const [currentStatus, setCurrentStatus] = useState<JobStatus>('Queued');
// // //   const [error, setError] = useState<string>('');
// // //
// // //   const handleFileSelect = (file: File) => {
// // //     setSelectedFile(file);
// // //     setError('');
// // //     setCurrentJob(null);
// // //   };
// // //
// // //   const handleNumVariantsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
// // //     const value = parseInt(e.target.value, 10);
// // //     if (value >= 1 && value <= 100) {
// // //       setNumVariants(value);
// // //     }
// // //   };
// // //
// // //   const handleSubmit = async (e: React.FormEvent) => {
// // //     e.preventDefault();
// // //
// // //     if (!selectedFile) {
// // //       setError('Vui lòng chọn file để upload');
// // //       return;
// // //     }
// // //
// // //     setError('');
// // //     setIsProcessing(true);
// // //     setUploadProgress(0);
// // //     setCurrentStatus('Queued');
// // //
// // //       try {
// // //       // BƯỚC 1: Gọi hàm createJob mới
// // //       // Hàm này thực hiện: Lấy Presigned URL -> Upload lên S3 -> Gửi lệnh Submit
// // //       const jobId = await ExamShufflingService.createJob(
// // //         selectedFile,
// // //         numVariants,
// // //         (progress: UploadProgress) => {
// // //           setUploadProgress(progress.percentage);
// // //         }
// // //       );
// // //
// // //       // BƯỚC 2: Khởi tạo thông tin Job để hiển thị ngay lập tức
// // //       const initialJob: UploadJob = {
// // //         jobId: jobId,
// // //         fileKey: '', // Frontend không cần quan tâm key này nữa
// // //         fileName: selectedFile.name,
// // //         status: 'Queued',
// // //         createdAt: Date.now(),
// // //         numVariants: numVariants,
// // //       };
// // //
// // //       setCurrentJob(initialJob);
// // //       setCurrentStatus('Queued');
// // //
// // //       // BƯỚC 3: Tự thực hiện Polling (Vòng lặp kiểm tra trạng thái)
// // //       // Vì hàm createJob trả về ngay sau khi upload xong, ta phải tự chờ Backend xử lý
// // //       let isJobFinished = false;
// // //
// // //       while (!isJobFinished) {
// // //         // Nghỉ 2 giây giữa các lần kiểm tra
// // //         await new Promise((resolve) => setTimeout(resolve, 2000));
// // //
// // //         // Gọi API lấy trạng thái mới nhất
// // //         const statusData: JobStatusResponse = await ExamShufflingService.getJobStatus(jobId);
// // //
// // //         // Cập nhật trạng thái vào State
// // //         setCurrentStatus(statusData.Status);
// // //
// // //         // Cập nhật thông tin Job (nếu có OutputUrl thì React sẽ hiện nút Download)
// // //         setCurrentJob((prevJob) => {
// // //             if (!prevJob) return null;
// // //             return {
// // //                 ...prevJob,
// // //                 status: statusData.Status,
// // //                 updatedAt: statusData.UpdatedAt,
// // //                 outputUrl: statusData.OutputUrl,
// // //                 outputKey: statusData.OutputKey
// // //             };
// // //         });
// // //
// // //         // Kiểm tra điều kiện thoát vòng lặp
// // //         if (statusData.Status === 'Done' || statusData.Status === 'Failed') {
// // //           isJobFinished = true;
// // //         }
// // //       }
// // //
// // //       // Khi vòng lặp kết thúc, code sẽ chạy xuống finally để set setIsProcessing(false)
// // //     } catch (err) {
// // //       setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
// // //       setCurrentStatus('Failed');
// // //     } finally {
// // //       setIsProcessing(false);
// // //     }
// // //   };
// // //
// // //   const handleReset = () => {
// // //     setSelectedFile(null);
// // //     setCurrentJob(null);
// // //     setError('');
// // //     setUploadProgress(0);
// // //     setCurrentStatus('Queued');
// // //   };
// // //
// // //   const handleDownload = () => {
// // //     if (currentJob?.outputUrl) {
// // //       window.open(currentJob.outputUrl, '_blank');
// // //     }
// // //   };
// // //
// // //   return (
// // //     <div className="app">
//              <div className="container">
//                  <header className="header">
//                  <h1>🎓 ExamShuffling</h1>
//                  <p>Hệ thống tự động tạo đề thi trắc nghiệm</p>
//               </header>
//
//         <div className="main-content">
//           <form onSubmit={handleSubmit} className="upload-form">
//             <FileUpload
//               onFileSelect={handleFileSelect}
//               disabled={isProcessing}
//             />
// // //
// // //             <div className="form-group">
// // //               <label htmlFor="numVariants">Số lượng đề thi cần tạo:</label>
// // //               <input
// // //                 type="number"
// // //                 id="numVariants"
// // //                 min="1"
// // //                 max="100"
// // //                 value={numVariants}
// // //                 onChange={handleNumVariantsChange}
// // //                 disabled={isProcessing}
// // //                 className="number-input"
// // //               />
// // //               <p className="input-hint">
// // //                 Hệ thống sẽ tạo {numVariants} mã đề khác nhau (từ 101 đến {100 + numVariants})
// // //               </p>
// // //             </div>
// // //
// // //             {error && (
// // //               <div className="error-message">
// // //                 {error}
// // //               </div>
// // //             )}
// // //
// // //             <div className="button-group">
// // //               <button
// // //                 type="submit"
// // //                 disabled={!selectedFile || isProcessing}
// // //                 className="submit-button"
// // //               >
// // //                 {isProcessing ? 'Đang xử lý...' : 'Bắt đầu xử lý'}
// // //               </button>
// // //
// // //               {currentJob && (
// // //                 <button
// // //                   type="button"
// // //                   onClick={handleReset}
// // //                   disabled={isProcessing}
// // //                   className="reset-button"
// // //                 >
// // //                   <RefreshCw size={18} />
// // //                   Làm mới
// // //                 </button>
// // //               )}
// // //             </div>
// // //           </form>
// // //
// // //           {(isProcessing || currentJob) && (
// // //             <ProgressTracker
// // //               status={currentStatus}
// // //               uploadProgress={uploadProgress}
// // //               errorMessage={error}
// // //             />
// // //           )}
// // //
// // //           {currentJob?.status === 'Done' && currentJob.outputUrl && (
// // //             <div className="result-card">
// // //               <h3>✅ Xử lý thành công!</h3>
// // //               <p>
// // //                 Đã tạo thành công {numVariants} mã đề thi và bảng đáp án.
// // //               </p>
// // //               <p className="file-info">
// // //                 <strong>File gốc:</strong> {currentJob.fileName}
// // //               </p>
// // //               <button
// // //                 onClick={handleDownload}
// // //                 className="download-button"
// // //               >
// // //                 <Download size={20} />
// // //                 Tải về file ZIP
// // //               </button>
// // //               <p className="download-hint">
// // //                 File ZIP chứa {numVariants} file docx (mã đề 101-{100 + numVariants})
// // //                 và 1 file Excel tổng hợp đáp án
// // //               </p>
// // //             </div>
// // //           )}
// // //         </div>
// // //
// // //         <footer className="footer">
// // //           <p>
// // //             Powered by AWS S3 + SQS + DynamoDB |
// // //             Backend: Python + boto3 |
// // //             Frontend: React + TypeScript
// // //           </p>
// // //         </footer>
// // //       </div>
// // //     </div>
// // //   );
// // // }
// // //
// // // export default App;
// // // import React, { useState } from 'react';
// // // import { FileUpload } from './components/FileUpload';
// // // import { ProgressTracker } from './components/ProgressTracker';
// // // // Import Component Preview vừa tạo
// // // import PreviewRenderer, { AssetMap } from './components/PreviewRenderer';
// // // import { ExamShufflingService } from './services/examShufflingService';
// // // import { UploadJob, JobStatus, UploadProgress, JobStatusResponse } from './types';
// // // import { Download, RefreshCw, Eye, Code } from 'lucide-react';
// // // import './App.css';
// // //
// // // // Định nghĩa URL Backend (nên đưa vào file config/env)
// // // const API_BASE_URL = 'http://localhost:5000';
// // //
// // // function App() {
// // //   const [selectedFile, setSelectedFile] = useState<File | null>(null);
// // //   const [numVariants, setNumVariants] = useState<number>(10);
// // //
// // //   // State cho quá trình Xử lý (Shuffling)
// // //   const [isProcessing, setIsProcessing] = useState(false);
// // //   const [uploadProgress, setUploadProgress] = useState<number>(0);
// // //   const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
// // //   const [currentStatus, setCurrentStatus] = useState<JobStatus>('Queued');
// // //   const [error, setError] = useState<string>('');
// // //
// // //   // State mới cho tính năng Preview
// // //   const [previewData, setPreviewData] = useState<{ raw_text: string; assets_map: AssetMap } | null>(null);
// // //   const [isPreviewLoading, setIsPreviewLoading] = useState(false);
// // //
// // //   // Hàm gọi API Preview riêng lẻ (bạn có thể đưa vào ExamShufflingService sau này)
// // //   const fetchPreview = async (file: File) => {
// // //     setIsPreviewLoading(true);
// // //     setPreviewData(null); // Reset preview cũ
// // //
// // //     const formData = new FormData();
// // //     formData.append('file', file);
// // //
// // //     try {
// // //       const response = await fetch(`${API_BASE_URL}/api/preview`, {
// // //         method: 'POST',
// // //         body: formData,
// // //       });
// // //       const result = await response.json();
// // //
// // //       if (result.status === 'success') {
// // //         setPreviewData(result.data);
// // //       } else {
// // //         console.error("Preview failed:", result.error);
// // //         // Không set Error chính (setError) để tránh chặn luồng submit chính
// // //       }
// // //     } catch (err) {
// // //       console.error("Preview network error:", err);
// // //     } finally {
// // //       setIsPreviewLoading(false);
// // //     }
// // //   };
// // //
// // //   const handleFileSelect = (file: File) => {
// // //     setSelectedFile(file);
// // //     setError('');
// // //     setCurrentJob(null);
// // //     setUploadProgress(0);
// // //     setCurrentStatus('Queued');
// // //
// // //     // Gọi ngay API Preview khi chọn file
// // //     fetchPreview(file);
// // //   };
// // //
// // //   const handleNumVariantsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
// // //     const value = parseInt(e.target.value, 10);
// // //     if (value >= 1 && value <= 100) {
// // //       setNumVariants(value);
// // //     }
// // //   };
// // //
// // //   const handleSubmit = async (e: React.FormEvent) => {
// // //     e.preventDefault();
// // //
// // //     if (!selectedFile) {
// // //       setError('Vui lòng chọn file để upload');
// // //       return;
// // //     }
// // //
// // //     setError('');
// // //     setIsProcessing(true);
// // //     setUploadProgress(0);
// // //     setCurrentStatus('Queued');
// // //
// // //     try {
// // //       // Logic cũ: Tạo Job trộn đề
// // //       const jobId = await ExamShufflingService.createJob(
// // //         selectedFile,
// // //         numVariants,
// // //         (progress: UploadProgress) => {
// // //           setUploadProgress(progress.percentage);
// // //         }
// // //       );
// // //
// // //       const initialJob: UploadJob = {
// // //         jobId: jobId,
// // //         fileKey: '',
// // //         fileName: selectedFile.name,
// // //         status: 'Queued',
// // //         createdAt: Date.now(),
// // //         numVariants: numVariants,
// // //       };
// // //
// // //       setCurrentJob(initialJob);
// // //       setCurrentStatus('Queued');
// // //
// // //       // Polling kiểm tra trạng thái
// // //       let isJobFinished = false;
// // //       while (!isJobFinished) {
// // //         await new Promise((resolve) => setTimeout(resolve, 2000));
// // //         const statusData: JobStatusResponse = await ExamShufflingService.getJobStatus(jobId);
// // //
// // //         setCurrentStatus(statusData.Status);
// // //         setCurrentJob((prevJob) => {
// // //             if (!prevJob) return null;
// // //             return {
// // //                 ...prevJob,
// // //                 status: statusData.Status,
// // //                 updatedAt: statusData.UpdatedAt,
// // //                 outputUrl: statusData.OutputUrl,
// // //                 outputKey: statusData.OutputKey
// // //             };
// // //         });
// // //
// // //         if (statusData.Status === 'Done' || statusData.Status === 'Failed') {
// // //           isJobFinished = true;
// // //         }
// // //       }
// // //     } catch (err) {
// // //       setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
// // //       setCurrentStatus('Failed');
// // //     } finally {
// // //       setIsProcessing(false);
// // //     }
// // //   };
// // //
// // //   const handleReset = () => {
// // //     setSelectedFile(null);
// // //     setPreviewData(null); // Reset preview
// // //     setCurrentJob(null);
// // //     setError('');
// // //     setUploadProgress(0);
// // //     setCurrentStatus('Queued');
// // //   };
// // //
// // //   const handleDownload = () => {
// // //     if (currentJob?.outputUrl) {
// // //       window.open(currentJob.outputUrl, '_blank');
// // //     }
// // //   };
// // //
// // //   return (
// // //     <div className="app">
// // //       <div className="container max-w-6xl mx-auto p-4"> {/* Tăng độ rộng container để chứa Split View */}
// // //         <header className="header text-center mb-8">
// // //           <h1 className="text-3xl font-bold text-gray-800">🎓 ExamShuffling</h1>
// // //           <p className="text-gray-600">Hệ thống tự động trộn đề thi trắc nghiệm</p>
// // //         </header>
// // //
// // //         <div className="main-content space-y-8">
// // //           {/* KHU VỰC 1: UPLOAD & CẤU HÌNH */}
// // //           <form onSubmit={handleSubmit} className="upload-form bg-white p-6 rounded-lg shadow-md">
// // //             <FileUpload
// // //               onFileSelect={handleFileSelect}
// // //               disabled={isProcessing}
// // //             />
// // //
// // //             {/* Chỉ hiện cấu hình khi đã chọn file */}
// // //             {selectedFile && (
// // //               <div className="mt-6 animate-fade-in">
// // //                 <div className="form-group mb-4">
// // //                   <label htmlFor="numVariants" className="block font-medium mb-2">Số lượng đề thi cần tạo:</label>
// // //                   <div className="flex items-center gap-4">
// // //                     <input
// // //                       type="number"
// // //                       id="numVariants"
// // //                       min="1"
// // //                       max="100"
// // //                       value={numVariants}
// // //                       onChange={handleNumVariantsChange}
// // //                       disabled={isProcessing}
// // //                       className="number-input border p-2 rounded w-24 text-center"
// // //                     />
// // //                     <span className="text-sm text-gray-500">
// // //                       (Tạo mã đề từ 101 đến {100 + numVariants})
// // //                     </span>
// // //                   </div>
// // //                 </div>
// // //
// // //                 <div className="button-group flex gap-4 mt-6">
// // //                   <button
// // //                     type="submit"
// // //                     disabled={isProcessing}
// // //                     className={`submit-button px-6 py-2 rounded text-white font-bold transition-colors ${
// // //                       isProcessing ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
// // //                     }`}
// // //                   >
// // //                     {isProcessing ? 'Đang xử lý...' : '⚡ Bắt đầu Trộn đề'}
// // //                   </button>
// // //
// // //                   <button
// // //                     type="button"
// // //                     onClick={handleReset}
// // //                     disabled={isProcessing}
// // //                     className="reset-button px-6 py-2 rounded border border-gray-300 hover:bg-gray-100 flex items-center gap-2"
// // //                   >
// // //                     <RefreshCw size={18} />
// // //                     Làm mới
// // //                   </button>
// // //                 </div>
// // //               </div>
// // //             )}
// // //
// // //             {error && (
// // //               <div className="error-message text-red-600 mt-4 p-3 bg-red-50 rounded border border-red-200">
// // //                 {error}
// // //               </div>
// // //             )}
// // //           </form>
// // //
// // //           {/* KHU VỰC 2: PREVIEW (SPLIT VIEW) */}
// // //           {/* Hiển thị khi đang loading preview HOẶC đã có dữ liệu preview */}
// // //           {/*{(isPreviewLoading || previewData) && (*/}
// // //           {/*  <div className="preview-section border-t pt-8">*/}
// // //           {/*    <h2 className="text-xl font-bold mb-4 flex items-center gap-2">*/}
// // //           {/*      <Eye size={24} className="text-blue-600"/>*/}
// // //           {/*      Xem trước nội dung*/}
// // //           {/*    </h2>*/}
// // //
// // //           {/*    {isPreviewLoading ? (*/}
// // //           {/*      <div className="flex justify-center items-center h-32 bg-gray-50 rounded border border-dashed">*/}
// // //           {/*        <p className="text-gray-500 animate-pulse">Đang phân tích đề thi...</p>*/}
// // //           {/*      </div>*/}
// // //           {/*    ) : (*/}
// // //           {/*      previewData && (*/}
// // //           {/*        <div className="split-view flex flex-col md:flex-row gap-4 h-[500px]"> /!* Chiều cao cố định để scroll *!/*/}
// // //
// // //           {/*          /!* Cột trái: Render Đẹp *!/*/}
// // //           {/*          <div className="view-pane flex-1 flex flex-col border rounded-lg overflow-hidden bg-white shadow-sm">*/}
// // //           {/*            <div className="pane-header bg-gray-100 p-2 border-b font-semibold flex justify-between items-center">*/}
// // //           {/*              <span>📄 Hiển thị</span>*/}
// // //           {/*              <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">Preview</span>*/}
// // //           {/*            </div>*/}
// // //           {/*            <div className="pane-content flex-1 overflow-auto bg-white">*/}
// // //           {/*              <PreviewRenderer*/}
// // //           {/*                rawText={previewData.raw_text}*/}
// // //           {/*                assetsMap={previewData.assets_map}*/}
// // //           {/*              />*/}
// // //           {/*            </div>*/}
// // //           {/*          </div>*/}
// // //
// // //           {/*          /!* Cột phải: Source Code *!/*/}
// // //           {/*          <div className="view-pane flex-1 flex flex-col border rounded-lg overflow-hidden bg-gray-900 text-white shadow-sm">*/}
// // //           {/*            <div className="pane-header bg-gray-800 p-2 border-b font-semibold flex justify-between items-center text-gray-300">*/}
// // //           {/*              <span className="flex items-center gap-2"><Code size={16}/> Mã nguồn</span>*/}
// // //           {/*              <span className="text-xs bg-gray-700 px-2 py-0.5 rounded">Read-only</span>*/}
// // //           {/*            </div>*/}
// // //           {/*            <textarea*/}
// // //           {/*              className="pane-content flex-1 w-full h-full bg-gray-900 text-gray-300 p-4 font-mono text-sm resize-none outline-none"*/}
// // //           {/*              value={previewData.raw_text}*/}
// // //           {/*              readOnly*/}
// // //           {/*            />*/}
// // //           {/*          </div>*/}
// // //           {/*        </div>*/}
// // //           {/*      )*/}
// // //           {/*    )}*/}
// // //           {/*  </div>*/}
// // //           {/*)}*/}
// // //             {/* KHU VỰC 2: PREVIEW (SPLIT VIEW) */}
// // //           {(isPreviewLoading || previewData) && (
// // //             <div className="preview-section">
// // //               <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
// // //                 <Eye size={24}/> Xem trước nội dung
// // //               </h2>
// // //
// // //               {isPreviewLoading ? (
// // //                 <div style={{padding: '50px', textAlign: 'center', background: '#f9f9f9', border: '2px dashed #ccc'}}>
// // //                   <p>⏳ Đang phân tích đề thi...</p>
// // //                 </div>
// // //               ) : (
// // //                 previewData && (
// // //                   // SỬ DỤNG CLASS CSS MỚI Ở ĐÂY
// // //                   <div className="split-view-container">
// // //
// // //                     {/* Cột trái: Render Đẹp */}
// // //                     <div className="view-pane">
// // //                       <div className="pane-header">
// // //                         <span>📄 Giao diện Đề thi</span>
// // //                         <span style={{fontSize: '0.8em', background: '#d1fae5', padding: '2px 8px', borderRadius: '4px', color: '#065f46'}}>Preview</span>
// // //                       </div>
// // //                       <div className="pane-content">
// // //                         <PreviewRenderer
// // //                           rawText={previewData.raw_text}
// // //                           assetsMap={previewData.assets_map}
// // //                         />
// // //                       </div>
// // //                     </div>
// // //
// // //                     {/* Cột phải: Source Code */}
// // //                     <div className="view-pane source-pane">
// // //                       <div className="pane-header" style={{background: '#333', color: '#fff', borderColor: '#444'}}>
// // //                         <span className="flex items-center gap-2"><Code size={16}/> Mã nguồn (Raw Text)</span>
// // //                         <span style={{fontSize: '0.8em', background: '#555', padding: '2px 8px', borderRadius: '4px'}}>Read-only</span>
// // //                       </div>
// // //                       <div className="pane-content">
// // //                         <textarea
// // //                           className="source-editor"
// // //                           value={previewData.raw_text}
// // //                           readOnly
// // //                         />
// // //                       </div>
// // //                     </div>
// // //
// // //                   </div>
// // //                 )
// // //               )}
// // //             </div>
// // //           )}
// // //           {/* KHU VỰC 3: KẾT QUẢ XỬ LÝ (Progress & Result) */}
// // //           {(isProcessing || currentJob) && (
// // //             <div className="processing-section border-t pt-8">
// // //                <ProgressTracker
// // //                 status={currentStatus}
// // //                 uploadProgress={uploadProgress}
// // //                 errorMessage={error}
// // //               />
// // //
// // //               {currentJob?.status === 'Done' && currentJob.outputUrl && (
// // //                 <div className="result-card mt-6 bg-green-50 border border-green-200 p-6 rounded-lg text-center animate-bounce-in">
// // //                   <h3 className="text-2xl font-bold text-green-700 mb-2">✅ Xử lý thành công!</h3>
// // //                   <p className="mb-4">
// // //                     Đã tạo thành công {numVariants} mã đề thi và bảng đáp án.
// // //                   </p>
// // //                   <button
// // //                     onClick={handleDownload}
// // //                     className="download-button bg-green-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-green-700 flex items-center gap-2 mx-auto shadow-lg transform hover:-translate-y-1 transition-all"
// // //                   >
// // //                     <Download size={24} />
// // //                     Tải về file ZIP kết quả
// // //                   </button>
// // //                 </div>
// // //               )}
// // //             </div>
// // //           )}
// // //         </div>
// // //
// // //         <footer className="footer text-center mt-12 text-gray-500 text-sm">
// // //           <p>Powered by AWS S3 + SQS + DynamoDB | Backend: Python (Flask) | Frontend: React</p>
// // //         </footer>
// // //       </div>
// // //     </div>
// // //   );
// // // }
// // //
// // // export default App;
// // import React, { useState } from 'react';
// // import PreviewRenderer, { AssetMap } from './components/PreviewRenderer';
// // import { ExamShufflingService } from './services/examShufflingService';
// // import { UploadJob } from './types';
// // import { Download, RefreshCw, UploadCloud, FileText, Settings, Play } from 'lucide-react';
// // import './App.css';
// //
// // const API_BASE_URL = 'http://localhost:5000';
// //
// // function App() {
// //   const [selectedFile, setSelectedFile] = useState<File | null>(null);
// //   const [numVariants, setNumVariants] = useState<number>(10);
// //   const [isProcessing, setIsProcessing] = useState(false);
// //   const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
// //   const [previewData, setPreviewData] = useState<{ raw_text: string; assets_map: AssetMap } | null>(null);
// //   const [isPreviewLoading, setIsPreviewLoading] = useState(false);
// //   const [error, setError] = useState<string>('');
// //
// //   // --- LOGIC GIỮ NGUYÊN ---
// //   const fetchPreview = async (file: File) => {
// //     setIsPreviewLoading(true);
// //     setPreviewData(null);
// //     const formData = new FormData();
// //     formData.append('file', file);
// //     try {
// //       const response = await fetch(`${API_BASE_URL}/api/preview`, { method: 'POST', body: formData });
// //       const result = await response.json();
// //       if (result.status === 'success') setPreviewData(result.data);
// //     } catch (err) { console.error(err); }
// //     finally { setIsPreviewLoading(false); }
// //   };
// //
// //   const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
// //     const file = e.target.files?.[0];
// //     if (file) {
// //       setSelectedFile(file);
// //       fetchPreview(file);
// //       // Reset trạng thái cũ
// //       setCurrentJob(null);
// //       setError('');
// //     }
// //   };
// //
// //   const handleSubmit = async () => {
// //     if (!selectedFile) return;
// //     setIsProcessing(true);
// //     try {
// //       const jobId = await ExamShufflingService.createJob(selectedFile, numVariants, () => {});
// //       // ... Logic polling giữ nguyên như cũ ...
// //       // Để code gọn, tôi giả lập đoạn này, bạn copy lại logic polling từ file cũ vào đây nhé
// //       let isJobFinished = false;
// //       while (!isJobFinished) {
// //         await new Promise((r) => setTimeout(r, 2000));
// //         const statusData = await ExamShufflingService.getJobStatus(jobId);
// //         if (statusData.Status === 'Done') {
// //             setCurrentJob({ jobId, fileName: selectedFile.name, status: 'Done', outputUrl: statusData.OutputUrl } as any);
// //             isJobFinished = true;
// //         }
// //       }
// //     } catch (err) { setError('Có lỗi xảy ra'); }
// //     finally { setIsProcessing(false); }
// //   };
// //   // -------------------------
// //
// //   return (
// //     // Container chính: Chiếm toàn bộ màn hình (h-screen), không cuộn body (overflow-hidden)
// //     <div className="flex flex-col h-screen bg-gray-100 overflow-hidden font-sans">
// //
// //       {/* 1. HEADER (THANH CÔNG CỤ) */}
// //       <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 shadow-sm z-10 shrink-0">
// //
// //         {/* Bên trái: Logo + Tên file */}
// //         <div className="flex items-center gap-4">
// //           <div className="flex items-center gap-2 text-blue-700 font-bold text-xl">
// //             <Settings className="w-6 h-6" />
// //             <span>ExamShuffling</span>
// //           </div>
// //
// //           {/* Nút Upload nhỏ gọn trên Header */}
// //           <div className="relative group">
// //             <input
// //               type="file"
// //               accept=".docx"
// //               onChange={handleFileChange}
// //               className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
// //             />
// //             <button className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded border border-gray-300 transition-colors text-sm font-medium">
// //               <UploadCloud size={16} />
// //               {selectedFile ? 'Đổi file khác' : 'Tải đề thi lên'}
// //             </button>
// //           </div>
// //
// //           {selectedFile && (
// //              <span className="text-sm text-gray-600 truncate max-w-[200px] border-l pl-3 border-gray-300">
// //                📄 {selectedFile.name}
// //              </span>
// //           )}
// //         </div>
// //
// //         {/* Bên phải: Cấu hình + Nút Action */}
// //         <div className="flex items-center gap-3">
// //             <div className="flex items-center gap-2 bg-gray-50 px-3 py-1.5 rounded border border-gray-200">
// //                 <span className="text-sm text-gray-600">Số mã đề:</span>
// //                 <input
// //                   type="number" min="1" max="100"
// //                   value={numVariants}
// //                   onChange={(e) => setNumVariants(parseInt(e.target.value))}
// //                   className="w-16 text-center text-sm font-bold bg-transparent outline-none border-b border-gray-300 focus:border-blue-500"
// //                 />
// //             </div>
// //
// //             {currentJob?.outputUrl ? (
// //                 <button
// //                   onClick={() => window.open(currentJob.outputUrl, '_blank')}
// //                   className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium shadow-sm transition-all"
// //                 >
// //                     <Download size={18} /> Tải kết quả
// //                 </button>
// //             ) : (
// //                 <button
// //                   onClick={handleSubmit}
// //                   disabled={!selectedFile || isProcessing}
// //                   className={`flex items-center gap-2 px-4 py-2 rounded font-medium text-white shadow-sm transition-all ${
// //                       !selectedFile || isProcessing ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
// //                   }`}
// //                 >
// //                     {isProcessing ? <RefreshCw className="animate-spin" size={18}/> : <Play size={18} fill="currentColor"/>}
// //                     {isProcessing ? 'Đang xử lý...' : 'Trộn đề ngay'}
// //                 </button>
// //             )}
// //         </div>
// //       </header>
// //
// //       {/* 2. MAIN CONTENT (SPLIT VIEW) */}
// //       <main className="flex-1 flex overflow-hidden relative">
// //         {/* Nếu chưa chọn file thì hiện màn hình Welcome */}
// //         {!selectedFile && !previewData && !isPreviewLoading ? (
// //             <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
// //                 <UploadCloud size={64} className="mb-4 text-gray-300"/>
// //                 <p className="text-lg">Vui lòng tải file đề thi (.docx) để bắt đầu</p>
// //             </div>
// //         ) : (
// //             // Giao diện 2 cột Full chiều cao
// //             <div className="flex w-full h-full">
// //
// //                 {/* CỘT TRÁI: PREVIEW (Giống Azota bên trái) */}
// //                 <div className="flex-1 flex flex-col border-r border-gray-200 bg-gray-50/50 min-w-0">
// //                     {/* Header nhỏ của cột */}
// //                     <div className="h-10 border-b border-gray-200 bg-white flex items-center justify-between px-3 shrink-0">
// //                         <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-1">
// //                             <FileText size={14}/> Xem trước đề thi
// //                         </span>
// //                         <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">Live Preview</span>
// //                     </div>
// //
// //                     {/* Nội dung cuộn độc lập */}
// //                     <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-white shadow-inner">
// //                         {isPreviewLoading ? (
// //                             <div className="flex flex-col items-center justify-center h-full space-y-3">
// //                                 <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
// //                                 <p className="text-gray-500 text-sm">Đang phân tích cấu trúc đề...</p>
// //                             </div>
// //                         ) : (
// //                             previewData && (
// //                                 <div className="max-w-[21cm] mx-auto bg-white min-h-full shadow-sm p-4 md:p-8">
// //                                     <PreviewRenderer
// //                                       rawText={previewData.raw_text}
// //                                       assetsMap={previewData.assets_map}
// //                                     />
// //                                 </div>
// //                             )
// //                         )}
// //                     </div>
// //                 </div>
// //
// //                 {/* CỘT PHẢI: SOURCE CODE (Giống Azota bên phải) */}
// //                 <div className="w-1/2 flex flex-col bg-[#1e1e1e] border-l border-gray-700 min-w-0">
// //                     <div className="h-10 border-b border-gray-700 bg-[#252526] flex items-center justify-between px-3 shrink-0">
// //                          <span className="text-xs font-bold text-gray-400 uppercase">Mã nguồn (Raw Text)</span>
// //                          <span className="text-[10px] text-gray-500">Read-only</span>
// //                     </div>
// //
// //                     <div className="flex-1 overflow-hidden relative">
// //                          <textarea
// //                            className="w-full h-full bg-[#1e1e1e] text-[#d4d4d4] p-4 font-mono text-sm resize-none outline-none custom-scrollbar leading-6"
// //                            value={previewData?.raw_text || ''}
// //                            readOnly
// //                            spellCheck={false}
// //                          />
// //                     </div>
// //                 </div>
// //
// //             </div>
// //         )}
// //       </main>
// //
// //       {/* Thông báo lỗi dạng Toast (nổi bên dưới) */}
// //       {error && (
// //         <div className="absolute bottom-5 right-5 bg-red-600 text-white px-4 py-2 rounded shadow-lg flex items-center gap-2 animate-bounce-in z-50">
// //             <span>⚠️ {error}</span>
// //             <button onClick={() => setError('')} className="ml-2 font-bold hover:text-red-200">✕</button>
// //         </div>
// //       )}
// //     </div>
// //   );
// // }
// //
// // export default App;
//
// import React, { useState } from 'react';
// import PreviewRenderer, { AssetMap } from './components/PreviewRenderer';
// import { ExamShufflingService } from './services/examShufflingService';
// import { UploadJob } from './types';
// import { Download, RefreshCw, UploadCloud, Settings, Play, Code, FileText, X, CheckCircle } from 'lucide-react';
// import './App.css';
//
// const API_BASE_URL = 'http://localhost:5000';
//
// function App() {
//   const [selectedFile, setSelectedFile] = useState<File | null>(null);
//   const [numVariants, setNumVariants] = useState<number>(10);
//   const [isProcessing, setIsProcessing] = useState(false);
//   const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
//   const [previewData, setPreviewData] = useState<{ raw_text: string; assets_map: AssetMap } | null>(null);
//   const [isPreviewLoading, setIsPreviewLoading] = useState(false);
//   const [error, setError] = useState<string>('');
//   const [uploadProgress, setUploadProgress] = useState<number>(0); // Giữ lại state này nếu muốn hiện thanh progress
//
//   // --- LOGIC GỌI API ---
//   const fetchPreview = async (file: File) => {
//     setIsPreviewLoading(true);
//     setPreviewData(null);
//     const formData = new FormData();
//     formData.append('file', file);
//     try {
//       const response = await fetch(`${API_BASE_URL}/api/preview`, { method: 'POST', body: formData });
//       const result = await response.json();
//       if (result.status === 'success') setPreviewData(result.data);
//     } catch (err) { console.error(err); }
//     finally { setIsPreviewLoading(false); }
//   };
//
//   const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
//     const file = e.target.files?.[0];
//     if (file) {
//       setSelectedFile(file);
//       fetchPreview(file);
//       // Reset trạng thái cũ
//       setCurrentJob(null);
//       setError('');
//     }
//   };
//
//   const handleReset = () => {
//     setSelectedFile(null);
//     setPreviewData(null);
//     setCurrentJob(null);
//     setError('');
//     setNumVariants(10);
//   };
//
//   const handleSubmit = async () => {
//     if (!selectedFile) return;
//     setIsProcessing(true);
//     try {
//       // Gọi API tạo job
//       const jobId = await ExamShufflingService.createJob(selectedFile, numVariants, (p) => setUploadProgress(p.percentage));
//
//       // Polling trạng thái
//       let isJobFinished = false;
//       while (!isJobFinished) {
//         await new Promise((r) => setTimeout(r, 2000));
//         const statusData = await ExamShufflingService.getJobStatus(jobId);
//         if (statusData.Status === 'Done') {
//             setCurrentJob({
//                 jobId, fileName: selectedFile.name, status: 'Done',
//                 outputUrl: statusData.OutputUrl, createdAt: Date.now(), numVariants
//             } as UploadJob);
//             isJobFinished = true;
//         } else if (statusData.Status === 'Failed') {
//             setError('Lỗi: ' + (statusData as any).LastError);
//             isJobFinished = true;
//         }
//       }
//     } catch (err) {
//         setError('Lỗi: ' + (err instanceof Error ? err.message : String(err)));
//     }
//     finally { setIsProcessing(false); }
//   };
//
//   // --- RENDER ---
//   return (
//     <div className={`app-container ${selectedFile ? 'mode-workspace' : 'mode-welcome'}`}>
//
//       {/* 1. HEADER (Chỉ hiện khi đã vào Workspace) */}
//       {selectedFile && (
//         <header className="app-header slide-down">
//           <div className="flex items-center gap-6">
//             <div className="logo cursor-pointer" onClick={handleReset}>
//               <div className="logo-icon bg-indigo-600 text-white p-1.5 rounded-lg">
//                  <Settings size={20} />
//               </div>
//               <span className="text-xl font-bold text-gray-800">ExamShuffling</span>
//             </div>
//
//             <div className="h-8 w-px bg-gray-200"></div>
//
//             <div className="file-badge">
//               <span className="text-gray-500 text-sm">File đang chọn:</span>
//               <span className="font-medium text-indigo-700 max-w-[200px] truncate" title={selectedFile.name}>
//                  {selectedFile.name}
//               </span>
//               <button onClick={handleReset} className="ml-2 text-gray-400 hover:text-red-500">
//                   <X size={16}/>
//               </button>
//             </div>
//           </div>
//
//           <div className="flex items-center gap-4">
//              {/* Cấu hình số lượng đề (Chuyển lên đây) */}
//              <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 rounded-lg border border-gray-200">
//                 <span className="text-sm font-medium text-gray-600">Số lượng đề:</span>
//                 <input
//                   type="number" min="1" max="100" value={numVariants}
//                   onChange={(e) => setNumVariants(parseInt(e.target.value))}
//                   className="w-12 bg-transparent text-center font-bold text-indigo-600 outline-none border-b border-gray-300 focus:border-indigo-500"
//                 />
//              </div>
//
//              {/* Nút Action */}
//              {currentJob?.outputUrl ? (
//                 <button
//                   onClick={() => window.open(currentJob.outputUrl, '_blank')}
//                   className="btn-action bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-200"
//                 >
//                     <Download size={20} /> Tải kết quả
//                 </button>
//              ) : (
//                 <button
//                   onClick={handleSubmit}
//                   disabled={isProcessing}
//                   className={`btn-action text-white shadow-lg shadow-indigo-200 ${isProcessing ? 'bg-gray-400' : 'bg-indigo-600 hover:bg-indigo-700'}`}
//                 >
//                     {isProcessing ? <RefreshCw className="animate-spin" size={20}/> : <Play size={20} fill="currentColor"/>}
//                     {isProcessing ? 'Đang xử lý...' : 'Bắt đầu Trộn'}
//                 </button>
//              )}
//           </div>
//         </header>
//       )}
//
//       {/* 2. MAIN CONTENT */}
//       <main className="main-content">
//
//         {/* TRẠNG THÁI 1: WELCOME SCREEN (MÀN HÌNH TÍM) */}
//         {!selectedFile && (
//             <div className="welcome-wrapper fade-in">
//                 <div className="logo-large mb-8 text-white flex flex-col items-center gap-3">
//                     <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-sm">
//                         <Settings size={48} className="text-white drop-shadow-md"/>
//                     </div>
//                     <h1 className="text-4xl font-extrabold tracking-tight drop-shadow-sm">ExamShuffling</h1>
//                     <p className="text-indigo-100 font-light text-lg">Hệ thống tự động trộn đề thi trắc nghiệm</p>
//                 </div>
//
//                 <div className="upload-card bg-white rounded-2xl shadow-2xl p-8 w-full max-w-xl text-center relative overflow-hidden">
//                     <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
//
//                     <div className="upload-zone border-2 border-dashed border-gray-300 rounded-xl p-10 flex flex-col items-center justify-center transition-all hover:border-indigo-500 hover:bg-indigo-50 group cursor-pointer relative">
//                         <input
//                             type="file" accept=".docx"
//                             onChange={handleFileChange}
//                             className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
//                         />
//                         <div className="bg-indigo-100 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300">
//                              <UploadCloud size={40} className="text-indigo-600" />
//                         </div>
//                         <h3 className="text-xl font-bold text-gray-800 mb-2">Kéo thả file vào đây</h3>
//                         <p className="text-gray-500 mb-6">hoặc</p>
//                         <button className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium shadow-md group-hover:shadow-lg transition-all">
//                             Chọn file từ máy tính
//                         </button>
//                         <p className="mt-4 text-xs text-gray-400">Chỉ chấp nhận file .docx (tối đa 50MB)</p>
//                     </div>
//                 </div>
//
//                 <p className="mt-8 text-white/60 text-sm">Powered by AWS Cloud • Fast & Secure</p>
//             </div>
//         )}
//
//         {/* TRẠNG THÁI 2: WORKSPACE (SPLIT VIEW) */}
//         {selectedFile && (
//             <div className="workspace-wrapper flex w-full h-full bg-gray-100 overflow-hidden animate-expand">
//                 {/* PREVIEW PANE */}
//                 <div className="flex-1 flex flex-col border-r border-gray-200 bg-gray-50/50 min-w-0">
//                     <div className="h-10 border-b border-gray-200 bg-white flex items-center justify-between px-4 shrink-0 shadow-sm z-10">
//                         <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
//                             <FileText size={14}/> Giao diện Đề thi
//                         </span>
//                         <span className="text-[10px] font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded border border-green-200 uppercase">Live Preview</span>
//                     </div>
//
//                     <div className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
//                         {isPreviewLoading ? (
//                             <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-20 backdrop-blur-sm">
//                                 <RefreshCw className="animate-spin text-indigo-600 mb-3" size={32}/>
//                                 <p className="text-gray-600 font-medium animate-pulse">Đang phân tích cấu trúc đề thi...</p>
//                             </div>
//                         ) : null}
//
//                         {previewData && (
//                             <div className="max-w-[21cm] mx-auto bg-white min-h-[29.7cm] shadow-lg border border-gray-200 p-10 transition-all origin-top animate-fade-in-up">
//                                 <PreviewRenderer
//                                     rawText={previewData.raw_text}
//                                     assetsMap={previewData.assets_map}
//                                 />
//                             </div>
//                         )}
//                     </div>
//                 </div>
//
//                 {/* CODE PANE */}
//                 <div className="w-[40%] flex flex-col bg-[#1e1e1e] border-l border-gray-700 min-w-0 shadow-2xl z-20">
//                      <div className="h-10 border-b border-[#333] bg-[#252526] flex items-center justify-between px-4 shrink-0">
//                          <span className="text-xs font-bold text-gray-400 uppercase flex items-center gap-2">
//                              <Code size={14}/> Mã nguồn (Raw Text)
//                          </span>
//                          <span className="text-[10px] text-gray-300 bg-[#3e3e42] px-2 py-0.5 rounded border border-[#4e4e52]">Read-only</span>
//                     </div>
//                     <div className="flex-1 relative overflow-hidden">
//                         <textarea
//                            className="w-full h-full bg-[#1e1e1e] text-[#d4d4d4] p-4 font-mono text-sm resize-none outline-none custom-scrollbar leading-6"
//                            value={previewData?.raw_text || ''}
//                            readOnly
//                            spellCheck={false}
//                          />
//                     </div>
//                 </div>
//             </div>
//         )}
//
//       </main>
//
//       {/* ERROR TOAST */}
//       {error && (
//         <div className="fixed bottom-6 right-6 bg-red-50 text-red-700 px-6 py-4 rounded-xl shadow-2xl border border-red-100 flex items-center gap-3 animate-bounce-in z-50 max-w-md">
//             <div className="bg-red-100 p-2 rounded-full">
//                 <X size={20} className="text-red-600"/>
//             </div>
//             <div>
//                 <p className="font-bold text-sm">Đã xảy ra lỗi</p>
//                 <p className="text-sm opacity-90">{error}</p>
//             </div>
//             <button onClick={() => setError('')} className="ml-auto text-red-400 hover:text-red-600"><X size={16}/></button>
//         </div>
//       )}
//
//       {/* SUCCESS TOAST (Khi xong job) */}
//       {currentJob?.status === 'Done' && (
//           <div className="fixed bottom-6 right-6 bg-white text-gray-800 px-6 py-4 rounded-xl shadow-2xl border border-green-100 flex items-center gap-4 animate-bounce-in z-50 max-w-md">
//             <div className="bg-green-100 p-2 rounded-full">
//                 <CheckCircle size={24} className="text-green-600"/>
//             </div>
//             <div>
//                 <p className="font-bold text-green-700">Xử lý hoàn tất!</p>
//                 <p className="text-sm text-gray-500">Đã tạo xong {numVariants} mã đề.</p>
//             </div>
//             <button
//                 onClick={() => window.open(currentJob.outputUrl, '_blank')}
//                 className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md transition-all"
//             >
//                 Tải về
//             </button>
//         </div>
//       )}
//     </div>
//   );
// }
//
// export default App;
import React, {useCallback, useEffect, useRef, useState} from 'react';
import PreviewRenderer, { AssetMap } from './components/PreviewRenderer';
import { ExamShufflingService } from './services/examShufflingService';
import { UploadJob } from './types';
import {
    Download,
    RefreshCw,
    UploadCloud,
    Settings,
    Play,
    Code,
    FileText,
    X,
    CheckCircle,
    Loader2,
    GripVertical, Edit3
} from 'lucide-react';
import './App.css';

const API_BASE_URL = 'http://localhost:5000';

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [numVariants, setNumVariants] = useState<number>(10);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
  const [previewData, setPreviewData] = useState<{ raw_text: string; assets_map: AssetMap } | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // State mới cho Overlay
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [showOverlay, setShowOverlay] = useState(false);
  const [leftWidth, setLeftWidth] = useState(60); // Mặc định cột trái chiếm 60%
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // --- LOGIC RESIZE ---
  const startResizing = useCallback(() => setIsResizing(true), []);
  const stopResizing = useCallback(() => setIsResizing(false), []);

  const resize = useCallback((mouseMoveEvent: MouseEvent) => {
    if (isResizing && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect();
        // Tính % độ rộng dựa trên vị trí chuột
        let newWidth = ((mouseMoveEvent.clientX - containerRect.left) / containerRect.width) * 100;
        // Giới hạn min/max (ví dụ: không nhỏ hơn 20% và không lớn hơn 80%)
        if (newWidth < 20) newWidth = 20;
        if (newWidth > 80) newWidth = 80;
        setLeftWidth(newWidth);
    }
  }, [isResizing]);

  useEffect(() => {
    window.addEventListener("mousemove", resize);
    window.addEventListener("mouseup", stopResizing);
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, [resize, stopResizing]);
  // --- LOGIC ---
  const fetchPreview = async (file: File) => {
    setIsPreviewLoading(true);
    setPreviewData(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${API_BASE_URL}/api/preview`, { method: 'POST', body: formData });
      const result = await response.json();
      if (result.status === 'success') setPreviewData(result.data);
    } catch (err) { console.error(err); }
    finally { setIsPreviewLoading(false); }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      fetchPreview(file);
      setCurrentJob(null);
      setError('');
      setUploadProgress(0);
    }
  };
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (previewData) {
      setPreviewData({
        ...previewData,
        raw_text: e.target.value // Cập nhật text mới ngay lập tức
      });
    }
  };
  const handleReset = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setCurrentJob(null);
    setError('');
    setNumVariants(10);
    setUploadProgress(0);
    setShowOverlay(false);
  };

  const closeOverlay = () => {
    // Chỉ cho tắt khi đã xong hoặc lỗi
    if (!isProcessing) {
        setShowOverlay(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setShowOverlay(true); // Mở Overlay ngay khi bấm nút
    setUploadProgress(0); // Reset progress

    try {
      // 1. Upload & Create Job
      const jobId = await ExamShufflingService.createJob(selectedFile, numVariants, (p) => {
          setUploadProgress(p.percentage);
      });

      // 2. Polling status
      let isJobFinished = false;
      while (!isJobFinished) {
        await new Promise((r) => setTimeout(r, 2000));
        const statusData = await ExamShufflingService.getJobStatus(jobId);

        if (statusData.Status === 'Done') {
            setCurrentJob({
                jobId, fileName: selectedFile.name, status: 'Done',
                outputUrl: statusData.OutputUrl, createdAt: Date.now(), numVariants
            } as UploadJob);
            isJobFinished = true;
        } else if (statusData.Status === 'Failed') {
            setError('Lỗi xử lý: ' + (statusData as any).LastError);
            isJobFinished = true;
        }
      }
    } catch (err) {
        setError('Lỗi: ' + (err instanceof Error ? err.message : String(err)));
    }
    finally {
        setIsProcessing(false);
        // Lưu ý: Không đóng Overlay ở đây để người dùng kịp nhìn thấy kết quả và bấm nút Download
    }
  };

  // --- RENDER ---
  return (
    <div className={`app-container ${selectedFile ? 'mode-workspace' : 'mode-welcome'}`}>

      {/* HEADER (Khi vào Workspace) */}
      {selectedFile && (
        <header className="app-header slide-down">
          <div className="flex items-center gap-6">
            <div className="logo cursor-pointer" onClick={handleReset}>
              <div className="logo-icon bg-indigo-600 text-white p-1.5 rounded-lg">
                 <Settings size={20} />
              </div>
              <span className="text-xl font-bold text-gray-800">ExamShuffling</span>
            </div>
            <div className="h-8 w-px bg-gray-200"></div>
            <div className="file-badge">
              <span className="text-gray-500 text-sm">File:</span>
              <span className="font-medium text-indigo-700 max-w-[200px] truncate" title={selectedFile.name}>
                 {selectedFile.name}
              </span>
              <button onClick={handleReset} className="ml-2 text-gray-400 hover:text-red-500">
                  <X size={16}/>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
             <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 rounded-lg border border-gray-200">
                <span className="text-sm font-medium text-gray-600">Số lượng đề:</span>
                <input
                  type="number" min="1" max="100" value={numVariants}
                  onChange={(e) => setNumVariants(parseInt(e.target.value))}
                  className="w-12 bg-transparent text-center font-bold text-indigo-600 outline-none border-b border-gray-300 focus:border-indigo-500"
                />
             </div>

             <button
                onClick={handleSubmit}
                disabled={isProcessing}
                className={`btn-action text-white shadow-lg shadow-indigo-200 ${isProcessing ? 'bg-gray-400' : 'bg-indigo-600 hover:bg-indigo-700'}`}
            >
                {isProcessing ? <RefreshCw className="animate-spin" size={20}/> : <Play size={20} fill="currentColor"/>}
                {isProcessing ? 'Đang xử lý...' : 'Bắt đầu Trộn'}
            </button>
          </div>
        </header>
      )}

      {/* MAIN CONTENT */}
      <main className="main-content">
        {!selectedFile && (
            // <div className="welcome-wrapper fade-in">
            //     <div className="logo-large mb-8 text-white flex flex-col items-center gap-3">
            //         <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-sm">
            //             <Settings size={48} className="text-white drop-shadow-md"/>
            //         </div>
            //         <h1 className="text-4xl font-extrabold tracking-tight drop-shadow-sm">ExamShuffling</h1>
            //         <p className="text-indigo-100 font-light text-lg">Hệ thống tự động trộn đề thi trắc nghiệm</p>
            //     </div>
            //
            //     <div className="upload-card bg-white rounded-2xl shadow-2xl p-8 w-full max-w-xl text-center relative overflow-hidden">
            //         <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
            //         <div className="upload-zone border-2 border-dashed border-gray-300 rounded-xl p-10 flex flex-col items-center justify-center transition-all hover:border-indigo-500 hover:bg-indigo-50 group cursor-pointer relative">
            //             <input
            //                 type="file" accept=".docx" onChange={handleFileChange}
            //                 className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            //             />
            //             <div className="bg-indigo-100 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300">
            //                  <UploadCloud size={40} className="text-indigo-600" />
            //             </div>
            //             <h3 className="text-xl font-bold text-gray-800 mb-2">Kéo thả file vào đây</h3>
            //             <p className="text-gray-500 mb-6">hoặc</p>
            //             <button className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium shadow-md">Chọn file từ máy tính</button>
            //         </div>
            //     </div>
            // </div>
            <div className="welcome-wrapper fade-in">
                <div className="flex flex-col items-center gap-2 mb-8 animate-fade-in-up">
                    {/*<div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center border border-white/30 shadow-inner mb-2">*/}
                    {/*    <Settings size={32} className="text-white drop-shadow-md" strokeWidth={2.5}/>*/}
                    {/*</div>*/}
                    <h1 className="text-3xl font-bold text-white tracking-wide">🎓 ExamShuffling</h1>
                    <p className="text-indigo-100 text-sm font-light opacity-90">Hệ thống tự động trộn đề thi trắc nghiệm</p>
                </div>

                {/* Upload Card - Đã bỏ phần input số lượng đề */}
                <div className="bg-white rounded-[20px] shadow-2xl p-6 w-[480px] animate-scale-up">
                    <div className="upload-zone border-2 border-dashed border-gray-300 rounded-[16px] h-[220px] flex flex-col items-center justify-center relative group hover:border-indigo-400 hover:bg-indigo-50/30 transition-all cursor-pointer">
                        <input
                            type="file"
                            accept=".docx"
                            onChange={handleFileChange}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        />

                        <div className="w-12 h-12 bg-indigo-50 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                             <UploadCloud size={24} className="text-indigo-600" strokeWidth={2.5} />
                        </div>

                        <h3 className="text-gray-900 font-bold text-lg mb-1">Kéo thả file vào đây</h3>
                        <p className="text-gray-400 text-sm mb-4">hoặc</p>

                        <button className="px-5 py-2 bg-indigo-600 text-white rounded-lg font-medium text-sm shadow-md hover:bg-indigo-700 transition-colors">
                            Chọn file từ máy tính
                        </button>
                    </div>
                </div>
            </div>
        )}

        {selectedFile && (
        //     <div className="workspace-wrapper flex w-full h-full bg-gray-100 overflow-hidden animate-expand">
        //         <div className="flex-1 flex flex-col border-r border-gray-200 bg-gray-50/50 min-w-0">
        //             <div className="h-10 border-b border-gray-200 bg-white flex items-center justify-between px-4 shrink-0 shadow-sm z-10">
        //                 <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
        //                     <FileText size={14}/> Giao diện Đề thi
        //                 </span>
        //                 <span className="text-[10px] font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded border border-green-200 uppercase">Live Preview</span>
        //             </div>
        //             <div className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
        //                 {isPreviewLoading && (
        //                     <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-20 backdrop-blur-sm">
        //                         <Loader2 className="animate-spin text-indigo-600 mb-3" size={32}/>
        //                         <p className="text-gray-600 font-medium animate-pulse">Đang phân tích cấu trúc...</p>
        //                     </div>
        //                 )}
        //                 {previewData && (
        //                     <div className="max-w-[21cm] mx-auto bg-white min-h-[29.7cm] shadow-lg border border-gray-200 p-10 transition-all origin-top animate-fade-in-up">
        //                         <PreviewRenderer rawText={previewData.raw_text} assetsMap={previewData.assets_map} />
        //                     </div>
        //                 )}
        //             </div>
        //         </div>
        //         <div
        //             className="w-1.5 bg-gray-300 hover:bg-indigo-500 cursor-col-resize flex items-center justify-center transition-colors z-50 hover:shadow-lg active:bg-indigo-600"
        //             onMouseDown={startResizing}
        //          >
        //             <GripVertical size={12} className="text-gray-400" />
        //         </div>
        //         <div className="w-[40%] flex flex-col bg-[#1e1e1e] border-l border-gray-700 min-w-0 shadow-2xl z-20">
        //              <div className="h-10 border-b border-[#333] bg-[#252526] flex items-center justify-between px-4 shrink-0">
        //                  <span className="text-xs font-bold text-gray-400 uppercase flex items-center gap-2">
        //                      <Code size={14}/> Mã nguồn (Raw Text)
        //                  </span>
        //             </div>
        //             <div className="flex-1 relative overflow-hidden">
        //                 <textarea
        //                    className="w-full h-full bg-[#1e1e1e] text-[#d4d4d4] p-4 font-mono text-sm resize-none outline-none custom-scrollbar leading-6"
        //                    value={previewData?.raw_text || ''}
        //                   // readOnly spellCheck={false}
        //                     onChange={handleTextChange}
        //                    spellCheck={false}
        //                    placeholder="Mã nguồn đề thi sẽ hiện ở đây..."
        //                  />
        //             </div>
        //         </div>
        //     </div>
        // )}
            <div className="workspace-wrapper flex w-full h-full bg-gray-100 overflow-hidden animate-expand" ref={containerRef}>

                {/* CỘT TRÁI: PREVIEW (Dynamic Width) */}
                <div
                    className="flex flex-col border-r border-gray-200 bg-gray-50/50 min-w-0 transition-none"
                    style={{ width: `${leftWidth}%` }}
                >
                    <div className="h-10 border-b border-gray-200 bg-white flex items-center justify-between px-4 shrink-0 shadow-sm z-10">
                        <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2"><FileText size={14}/> Giao diện Đề thi</span>
                        <span className="text-[10px] font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded border border-green-200 uppercase">Live Preview</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
                        {isPreviewLoading && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-20 backdrop-blur-sm">
                                <Loader2 className="animate-spin text-indigo-600 mb-3" size={32}/>
                                <p className="text-gray-600 font-medium animate-pulse">Đang phân tích cấu trúc...</p>
                            </div>
                        )}
                        {previewData && (
                            <div className="max-w-[21cm] mx-auto bg-white min-h-[29.7cm] shadow-lg border border-gray-200 p-10 transition-all origin-top animate-fade-in-up preview-paper">
                                <PreviewRenderer rawText={previewData.raw_text} assetsMap={previewData.assets_map} />
                            </div>
                        )}
                    </div>
                </div>

                {/* THANH RESIZER (Nắm kéo) */}
                <div
                    className="w-1.5 bg-gray-300 hover:bg-indigo-500 cursor-col-resize flex items-center justify-center transition-colors z-50 hover:shadow-lg active:bg-indigo-600"
                    onMouseDown={startResizing}
                >
                    <GripVertical size={12} className="text-gray-400" />
                </div>

                {/* CỘT PHẢI: EDITOR (Dynamic Width) */}
                <div
                    className="flex flex-col bg-[#1e1e1e] border-l border-gray-700 min-w-0 shadow-2xl z-20 transition-none"
                    style={{ width: `${100 - leftWidth}%` }}
                >
                     <div className="h-10 border-b border-[#333] bg-[#252526] flex items-center justify-between px-4 shrink-0">
                         <span className="text-xs font-bold text-gray-400 uppercase flex items-center gap-2">
                             <Code size={14}/> Mã nguồn (Editor)
                         </span>
                         <span className="text-[10px] text-blue-300 bg-blue-900/30 px-2 py-0.5 rounded border border-blue-800 flex items-center gap-1">
                            <Edit3 size={10}/> Editable
                         </span>
                    </div>
                    <div className="flex-1 relative overflow-hidden">
                        <textarea
                           className="w-full h-full bg-[#1e1e1e] text-[#d4d4d4] p-4 font-mono text-sm resize-none outline-none custom-scrollbar leading-6 focus:bg-[#252526] transition-colors"
                           value={previewData?.raw_text || ''}
                           onChange={handleTextChange}
                           spellCheck={false}
                           placeholder="Mã nguồn đề thi sẽ hiện ở đây..."
                         />
                    </div>
                </div>
            </div>
        )}
      </main>

      {/* --- NEW: PROGRESS OVERLAY --- */}
      {showOverlay && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center animate-fade-in">
            <div className="bg-white rounded-[32px] p-8 w-[420px] shadow-2xl flex flex-col items-center text-center relative animate-scale-up">

                {/* Nút tắt (chỉ hiện khi xong hoặc lỗi) */}
                {!isProcessing && (
                    <button onClick={closeOverlay} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors">
                        <X size={20}/>
                    </button>
                )}

                {/* TRƯỜNG HỢP 1: ĐANG XỬ LÝ (Processing) */}
                {isProcessing && (
                   <>
                     <div className="w-16 h-16 mb-6 relative">
                        {/* Vòng tròn loading */}
                        <div className="absolute inset-0 border-4 border-indigo-100 rounded-full"></div>
                        <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
                     </div>

                     <h3 className="text-xl font-bold text-gray-800 mb-2">Đang xử lý đề thi...</h3>

                     {uploadProgress < 100 ? (
                        <p className="text-gray-500 mb-6">Đang tải file lên server ({uploadProgress}%)</p>
                     ) : (
                        <p className="text-gray-500 mb-6">Đang trộn câu hỏi và tạo {numVariants} mã đề...</p>
                     )}

                     {/* Thanh Progress Bar */}
                     <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-indigo-600 transition-all duration-300 ease-out"
                            style={{ width: uploadProgress < 100 ? `${uploadProgress}%` : '100%' }}
                        >
                            {/* Hiệu ứng sọc chạy chạy khi đã 100% upload */}
                            {uploadProgress === 100 && (
                                <div className="w-full h-full animate-pulse bg-white/30"></div>
                            )}
                        </div>
                     </div>
                   </>
                )}

                {/* TRƯỜNG HỢP 2: THÀNH CÔNG (Success) */}
                {!isProcessing && currentJob?.status === 'Done' && (
                    <>
                        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-4 animate-bounce-small">
                            <CheckCircle size={40} className="text-green-600" />
                        </div>
                        <h3 className="text-2xl font-bold text-gray-800 mb-2">Hoàn tất!</h3>
                        <p className="text-gray-500 mb-6">Đã tạo thành công {numVariants} mã đề thi.</p>

                        <button
                            onClick={() => window.open(currentJob.outputUrl, '_blank')}
                            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 group"
                        >
                            <Download size={20} className="group-hover:translate-y-1 transition-transform"/>
                            Tải kết quả về máy
                        </button>

                        <p className="mt-4 text-xs text-gray-400">File ZIP bao gồm đề thi (.docx) và đáp án (.xlsx)</p>
                    </>
                )}

                {/* TRƯỜNG HỢP 3: LỖI (Error) */}
                {!isProcessing && error && (
                    <>
                         <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-4">
                            <X size={40} className="text-red-600" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-800 mb-2">Đã xảy ra lỗi</h3>
                        <p className="text-red-500 bg-red-50 p-3 rounded-lg text-sm mb-6 w-full break-words">
                            {error}
                        </p>
                        <button
                            onClick={closeOverlay}
                            className="px-6 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-50"
                        >
                            Đóng và thử lại
                        </button>
                    </>
                )}
            </div>
        </div>
      )}

    </div>
  );
}

export default App;