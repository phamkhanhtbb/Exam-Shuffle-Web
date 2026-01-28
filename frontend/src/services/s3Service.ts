// import { PutObjectCommand } from '@aws-sdk/client-s3';
// import { s3Client, AWS_CONFIG } from '../config/aws';
// import { UploadProgress } from '../types';
//
// export class S3Service {
//   /**
//    * Upload file lên S3 bucket input
//    */
//   static async uploadFile(
//     file: File,
//     onProgress?: (progress: UploadProgress) => void
//   ): Promise<string> {
//     const timestamp = Date.now();
//     const sanitizedFileName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
//     const fileKey = `${timestamp}_${sanitizedFileName}`;
//
//     try {
//       // Đọc file thành ArrayBuffer
//       const arrayBuffer = await file.arrayBuffer();
//       const buffer = new Uint8Array(arrayBuffer);
//
//       const command = new PutObjectCommand({
//         Bucket: AWS_CONFIG.s3BucketInput,
//         Key: fileKey,
//         Body: buffer,
//         ContentType: file.type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
//       });
//
//       // Simulate progress (AWS SDK v3 không hỗ trợ progress callback trực tiếp cho browser)
//       if (onProgress) {
//         onProgress({ loaded: 0, total: file.size, percentage: 0 });
//       }
//
//       await s3Client.send(command);
//
//       if (onProgress) {
//         onProgress({ loaded: file.size, total: file.size, percentage: 100 });
//       }
//
//       console.log(`✅ File uploaded successfully: s3://${AWS_CONFIG.s3BucketInput}/${fileKey}`);
//       return fileKey;
//     } catch (error) {
//       console.error('❌ Error uploading file to S3:', error);
//       throw new Error(`Failed to upload file: ${error instanceof Error ? error.message : 'Unknown error'}`);
//     }
//   }
//
//   /**
//    * Validate file before upload
//    */
//   static validateFile(file: File): { valid: boolean; error?: string } {
//     const maxSize = 50 * 1024 * 1024; // 50MB
//     const allowedTypes = [
//       'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
//       'application/msword',
//     ];
//
//     if (file.size > maxSize) {
//       return { valid: false, error: 'File size exceeds 50MB limit' };
//     }
//
//     if (!allowedTypes.includes(file.type) && !file.name.endsWith('.docx')) {
//       return { valid: false, error: 'Only .docx files are allowed' };
//     }
//
//     return { valid: true };
//   }
// }
import { UploadProgress } from '../types';

export class S3Service {
  /**
   * Upload file trực tiếp lên S3 thông qua Presigned URL
   * Không cần AWS Credentials ở đây!
   */
  static async uploadWithPresignedUrl(
    file: File,
    presignedUrl: string,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.open('PUT', presignedUrl, true);
      xhr.setRequestHeader('Content-Type', file.type);

      // Theo dõi tiến trình upload
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percentage = Math.round((event.loaded / event.total) * 100);
          onProgress({
            loaded: event.loaded,
            total: event.total,
            percentage,
          });
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          console.log('✅ Uploaded to S3 successfully');
          resolve();
        } else {
          reject(new Error(`Upload failed with status: ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error('Network error during upload'));

      xhr.send(file);
    });
  }
}