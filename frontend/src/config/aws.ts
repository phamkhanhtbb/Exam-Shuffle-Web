import { S3Client } from '@aws-sdk/client-s3';
import { SQSClient } from '@aws-sdk/client-sqs';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';

const REGION = process.env.REACT_APP_AWS_REGION || 'ap-southeast-1';

const credentials = {
  accessKeyId: process.env.REACT_APP_AWS_ACCESS_KEY_ID || '',
  secretAccessKey: process.env.REACT_APP_AWS_SECRET_ACCESS_KEY || '',
};

// S3 Client
export const s3Client = new S3Client({
  region: REGION,
  credentials,
});

// SQS Client
export const sqsClient = new SQSClient({
  region: REGION,
  credentials,
});

// DynamoDB Client
const dynamoDBClient = new DynamoDBClient({
  region: REGION,
  credentials,
});

export const docClient = DynamoDBDocumentClient.from(dynamoDBClient);

// Configuration constants
export const AWS_CONFIG = {
  region: REGION,
  s3BucketInput: process.env.REACT_APP_S3_BUCKET_INPUT || 'app-docx-input-team1',
  s3BucketOutput: process.env.REACT_APP_S3_BUCKET_OUTPUT || 'app-docx-output-team1',
  sqsQueueUrl: process.env.REACT_APP_SQS_QUEUE_URL || '',
  dynamoDBTable: process.env.REACT_APP_DYNAMODB_TABLE || 'ExamShufflingJobs',
  presignExpiresIn: parseInt(process.env.REACT_APP_PRESIGN_EXPIRES_IN || '3600', 10),
};
