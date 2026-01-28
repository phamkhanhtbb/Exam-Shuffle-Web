import { SendMessageCommand } from '@aws-sdk/client-sqs';
import { sqsClient, AWS_CONFIG } from '../config/aws';

export interface CreateJobPayload {
  jobId: string;
  fileKey: string;
  numVariants: number;
  permutation?: number[];
}

export class SQSService {
  /**
   * Gửi job message vào SQS queue
   */
  static async sendJobMessage(payload: CreateJobPayload): Promise<string> {
    const messageBody = {
      jobId: payload.jobId,
      fileKey: payload.fileKey,
      numVariants: payload.numVariants,
      permutation: payload.permutation,
    };

    try {
      const command = new SendMessageCommand({
        QueueUrl: AWS_CONFIG.sqsQueueUrl,
        MessageBody: JSON.stringify(messageBody),
      });

      const response = await sqsClient.send(command);
      console.log(`✅ Job message sent to SQS: ${response.MessageId}`);
      return response.MessageId || '';
    } catch (error) {
      console.error('❌ Error sending message to SQS:', error);
      throw new Error(`Failed to send job to queue: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}
