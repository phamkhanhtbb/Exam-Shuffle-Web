// import { v4 as uuidv4 } from 'uuid';
// import { S3Service } from './s3Service';
// import { SQSService } from './sqsService';
// import { DynamoDBService } from './dynamoDBService';
// import { UploadJob, JobStatusResponse, UploadProgress } from '../types';
//
// export interface UploadOptions {
//   numVariants: number;
//   onProgress?: (progress: UploadProgress) => void;
//   onStatusChange?: (status: JobStatusResponse) => void;
// }
//
// export class ExamShufflingService {
//   /**
//    * Main workflow: Upload → Create Job → Send to Queue → Poll Status
//    */
//   static async processFile(
//     file: File,
//     options: UploadOptions
//   ): Promise<UploadJob> {
//     const { numVariants, onProgress, onStatusChange } = options;
//
//     // 1. Validate file
//     const validation = S3Service.validateFile(file);
//     if (!validation.valid) {
//       throw new Error(validation.error);
//     }
//
//     // 2. Generate unique job ID
//     const jobId = `JOB-${uuidv4()}`;
//     console.log(`🚀 Starting job: ${jobId}`);
//
//     try {
//       // 3. Upload file to S3
//       console.log('📤 Step 1/4: Uploading file to S3...');
//       const fileKey = await S3Service.uploadFile(file, onProgress);
//
//       // 4. Create job record in DynamoDB
//       console.log('📝 Step 2/4: Creating job record in DynamoDB...');
//       await DynamoDBService.createJobRecord(jobId, fileKey, file.name, numVariants);
//
//       // 5. Send message to SQS
//       console.log('📨 Step 3/4: Sending job to processing queue...');
//       await SQSService.sendJobMessage({
//         jobId,
//         fileKey,
//         numVariants,
//       });
//
//       // 6. Start polling for job status
//       console.log('⏳ Step 4/4: Monitoring job progress...');
//       const finalStatus = await DynamoDBService.pollJobStatus(
//         jobId,
//         (status) => {
//           console.log(`📊 Job status: ${status.Status}`);
//           if (onStatusChange) {
//             onStatusChange(status);
//           }
//         },
//         60, // 60 attempts
//         5000 // Poll every 5 seconds
//       );
//
//       // 7. Return completed job info
//       const job: UploadJob = {
//         jobId,
//         fileKey,
//         fileName: file.name,
//         status: finalStatus.Status,
//         createdAt: finalStatus.CreatedAt || Date.now(),
//         updatedAt: finalStatus.UpdatedAt,
//         outputUrl: finalStatus.OutputUrl,
//         outputKey: finalStatus.OutputKey,
//         lastError: finalStatus.LastError,
//         numVariants,
//       };
//
//       console.log(`✅ Job completed: ${jobId}`);
//       return job;
//     } catch (error) {
//       console.error(`❌ Job failed: ${jobId}`, error);
//       throw error;
//     }
//   }
//
//   /**
//    * Check job status without polling
//    */
//   static async getJobStatus(jobId: string): Promise<JobStatusResponse | null> {
//     return DynamoDBService.getJobStatus(jobId);
//   }
// }
import { UploadJob, JobStatusResponse, UploadProgress } from '../types';

// Cấu hình đường dẫn API (Trỏ về server.py đang chạy)
const API_URL = 'http://localhost:5000/api';

export interface UploadOptions {
  numVariants: number;
  onProgress?: (progress: UploadProgress) => void; // Lưu ý: Fetch API mặc định khó track upload progress chi tiết như Axios, nên tạm thời có thể bỏ qua hoặc dùng XMLHttpRequest nếu cần.
  onStatusChange?: (status: JobStatusResponse) => void;
}

export class ExamShufflingService {

  /**
   * Quy trình mới: Upload file lên Python Server -> Nhận JobID -> Polling API Status
   */
  static async processFile(
    file: File,
    options: UploadOptions
  ): Promise<UploadJob> {
    const { numVariants, onStatusChange } = options;

    // 1. Validate sơ bộ (Backend sẽ check kỹ hơn)
    const validExtensions = ['.docx', '.doc'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!validExtensions.includes(fileExtension)) {
      throw new Error('Chỉ chấp nhận file .docx hoặc .doc');
    }

    try {
      // 2. Gọi API Upload (POST /api/upload)
      console.log('📤 Step 1/3: Uploading file to Backend...');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('numVariants', numVariants.toString());

      const uploadRes = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) {
        const errorData = await uploadRes.json();
        throw new Error(errorData.error || 'Upload failed');
      }

      const { JobId } = await uploadRes.json();
      console.log(`🚀 Job started: ${JobId}`);

      // 3. Bắt đầu Polling (Hỏi trạng thái liên tục)
      console.log('⏳ Step 2/3: Polling status from Backend...');

      const finalStatus = await this.pollJobStatus(JobId, (status) => {
        console.log(`📊 Job status: ${status.Status}`);
        if (onStatusChange) {
          onStatusChange(status);
        }
      });

      // 4. Trả về kết quả hoàn tất
      const job: UploadJob = {
        jobId: JobId,
        fileKey: '', // Frontend không cần biết key S3 nữa
        fileName: file.name,
        status: finalStatus.Status,
        createdAt: finalStatus.CreatedAt || Date.now(),
        updatedAt: finalStatus.UpdatedAt,
        outputUrl: finalStatus.OutputUrl,
        outputKey: finalStatus.OutputKey,
        lastError: finalStatus.LastError,
        numVariants,
      };

      console.log(`✅ Job completed: ${JobId}`);
      return job;

    } catch (error) {
      console.error(`❌ Process failed:`, error);
      throw error;
    }
  }

  /**
   * Hàm Polling riêng biệt gọi API GET /api/status/<id>
   */
  private static async pollJobStatus(
    jobId: string,
    onStatus: (status: JobStatusResponse) => void,
    maxAttempts = 60,
    intervalMs = 3000
  ): Promise<JobStatusResponse> {

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      // Gọi API lấy trạng thái
      const res = await fetch(`${API_URL}/status/${jobId}`);

      if (!res.ok) {
         // Nếu lỗi mạng tạm thời thì bỏ qua, chờ lần sau
         console.warn(`Polling attempt ${attempt} failed`);
      } else {
        const statusData: JobStatusResponse = await res.json();

        // Bắn callback ra ngoài UI cập nhật
        onStatus(statusData);

        // Kiểm tra điều kiện dừng
        if (statusData.Status === 'Done') {
          return statusData;
        }

        if (statusData.Status === 'Failed') {
          throw new Error(statusData.LastError || 'Job processing failed on server');
        }
      }

      // Chờ một chút trước khi hỏi tiếp (Delay)
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }

    throw new Error('Polling timeout: Server xử lý quá lâu.');
  }

  /**
   * Lấy trạng thái lẻ (nếu cần dùng ở chỗ khác)
   */
  static async getJobStatus(jobId: string): Promise<JobStatusResponse | null> {
    try {
      const res = await fetch(`${API_URL}/status/${jobId}`);
      if (res.ok) return await res.json();
      return null;
    } catch {
      return null;
    }
  }
}