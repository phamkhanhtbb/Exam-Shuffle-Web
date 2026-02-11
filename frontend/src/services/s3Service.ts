import { UploadProgress } from '../types';

export class S3Service {
  /**
   * Upload file directly to S3 using a Presigned URL.
   * No AWS Credentials required here!
   */
  static async uploadWithPresignedUrl(
    file: File,
    presignedUrl: string,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.open('PUT', presignedUrl, true);
      // Important: Content-Type must match what was used to sign the URL
      xhr.setRequestHeader('Content-Type', file.type);

      // Track upload progress
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