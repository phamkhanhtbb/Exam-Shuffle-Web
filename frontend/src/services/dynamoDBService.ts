import { PutCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import { docClient, AWS_CONFIG } from '../config/aws';
import { JobStatusResponse } from '../api/types';

type JobStatus = 'PendingUpload' | 'Queued' | 'Processing' | 'Done' | 'Failed';

export class DynamoDBService {
  /**
   * Tạo record mới trong DynamoDB với status = Queued
   */
  static async createJobRecord(
    jobId: string,
    fileKey: string,
    fileName: string,
    numVariants: number
  ): Promise<void> {
    const timestamp = Math.floor(Date.now() / 1000);

    const item = {
      JobId: jobId,
      Status: 'Queued' as JobStatus,
      FileKey: fileKey,
      FileName: fileName,
      NumVariants: numVariants,
      CreatedAt: timestamp,
      UpdatedAt: timestamp,
      // TTL: 1 giờ sau khi tạo
      ExpiresAt: timestamp + 3600,
    };

    try {
      const command = new PutCommand({
        TableName: AWS_CONFIG.dynamoDBTable,
        Item: item,
      });

      await docClient.send(command);
      console.log(`✅ Job record created in DynamoDB: ${jobId}`);
    } catch (error) {
      console.error('❌ Error creating job record:', error);
      throw new Error(`Failed to create job record: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Lấy thông tin job từ DynamoDB
   */
  static async getJobStatus(jobId: string): Promise<JobStatusResponse | null> {
    try {
      const command = new GetCommand({
        TableName: AWS_CONFIG.dynamoDBTable,
        Key: { JobId: jobId },
      });

      const response = await docClient.send(command);

      if (!response.Item) {
        return null;
      }

      return response.Item as JobStatusResponse;
    } catch (error) {
      console.error('❌ Error getting job status:', error);
      throw new Error(`Failed to get job status: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Polling job status cho đến khi Done hoặc Failed
   */
  static async pollJobStatus(
    jobId: string,
    onStatusChange: (status: JobStatusResponse) => void,
    maxAttempts: number = 60,
    intervalMs: number = 5000
  ): Promise<JobStatusResponse> {
    return new Promise((resolve, reject) => {
      let attempts = 0;

      const poll = async () => {
        attempts++;

        try {
          const status = await this.getJobStatus(jobId);

          if (!status) {
            if (attempts >= maxAttempts) {
              reject(new Error('Job not found'));
              return;
            }
            setTimeout(poll, intervalMs);
            return;
          }

          onStatusChange(status);

          if (status.Status === 'Done' || status.Status === 'Failed') {
            resolve(status);
            return;
          }

          if (attempts >= maxAttempts) {
            reject(new Error('Polling timeout'));
            return;
          }

          setTimeout(poll, intervalMs);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }
}
