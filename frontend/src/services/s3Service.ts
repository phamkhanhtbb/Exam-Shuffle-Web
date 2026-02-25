import { UploadProgress } from '../types';

/**
 * S3 SERVICE
 * 
 * Logic for moving files directly from the browser's memory to AWS S3.
 * Uses vanilla XMLHttpRequest to track upload progress efficiently.
 */
export class S3Service {
  /**
   * Upload file directly to S3 using a Presigned URL.
   * No AWS Credentials are required in the client as the URL contains the signature.
   */
  static async uploadWithPresignedUrl(
    file: File,
    presignedUrl: string,
    onProgress?: (progress: UploadProgress) => void,
    contentType?: string
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Open a PUT request to the presigned URL.
      xhr.open('PUT', presignedUrl, true);

      // CRITICAL: The Content-Type MUST match the one used during URL signing on the backend.
      // Use provided contentType if available, otherwise fallback to file.type
      const typeToUse = contentType || file.type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      xhr.setRequestHeader('Content-Type', typeToUse);

      /**
       * Track upload byte progress and emit events back to the hook.
       */
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

      /**
       * Handle successful upload completion.
       */
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          console.log('✅ Uploaded to S3 successfully');
          resolve();
        } else {
          // Failure if S3 returns 403 (expired) or 400 (bad signature).
          console.error(`❌ S3 Upload failed with status ${xhr.status}:`, xhr.responseText);
          reject(new Error(`Upload failed with status: ${xhr.status}`));
        }
      };

      /**
       * Handle network failures.
       */
      xhr.onerror = () => {
        console.error('❌ Network error during upload to S3. URL:', presignedUrl);
        console.error('Check CORS policy or proxy/VPN settings.');
        reject(new Error('Network error during upload'));
      };

      // Send the raw binary file content.
      xhr.send(file);
    });
  }
}