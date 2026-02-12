"""
AWS Service Layer — centralizes all AWS client initialization and operations.
Provides typed wrappers for S3, SQS, and DynamoDB interactions.
"""
import os
import json
import time
import uuid
import logging
from decimal import Decimal

import boto3
from botocore.config import Config
from config import settings

logger = logging.getLogger("server.aws")


class AwsService:
    """Singleton-style service for all AWS operations."""

    def __init__(self):
        # Explicitly disable proxies to avoid system/registry proxy issues
        my_config = Config(
            region_name=settings.region,
            proxies={}
        )

        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.region,
        )
        self.s3 = session.client('s3', config=my_config)
        self.sqs = session.client('sqs', config=my_config)
        dynamodb = session.resource('dynamodb', config=my_config)
        self.table = dynamodb.Table(settings.table_name)

    # --- S3 Operations ---

    def generate_presigned_upload_url(
        self, job_id: str, file_name: str, file_type: str
    ) -> tuple[str, str]:
        """
        Generate a presigned S3 PUT URL for file upload.
        Returns (presigned_url, s3_key).
        """
        safe_name = "".join(c for c in file_name if c.isalnum() or c in "._- ")
        s3_key = f"uploads/{job_id}/{safe_name}"

        presigned_url = self.s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.bucket_input,
                'Key': s3_key,
                'ContentType': file_type,
            },
            ExpiresIn=300,
        )
        return presigned_url, s3_key

    # --- DynamoDB Operations ---

    def create_job_record(self, job_id: str, file_name: str) -> None:
        """Create an initial job record with PendingUpload status."""
        timestamp = int(time.time())
        self.table.put_item(
            Item={
                'JobId': job_id,
                'Status': 'PendingUpload',
                'FileName': file_name,
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp,
            }
        )

    def update_job_status(
        self, job_id: str, status: str, num_variants: int | None = None
    ) -> None:
        """Update job status in DynamoDB."""
        timestamp = int(time.time())
        update_expr = "SET #s = :status, UpdatedAt = :ts"
        attr_names = {'#s': 'Status'}
        attr_values = {':status': status, ':ts': timestamp}

        if num_variants is not None:
            update_expr += ", NumVariants = :num"
            attr_values[':num'] = num_variants

        self.table.update_item(
            Key={'JobId': job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
        )

    def get_job_item(self, job_id: str) -> dict | None:
        """
        Retrieve a job item from DynamoDB.
        Returns the item dict or None if not found.
        """
        response = self.table.get_item(Key={'JobId': job_id})
        return response.get('Item')

    @staticmethod
    def decimal_convert(obj):
        """Convert DynamoDB Decimal types to int/float."""
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return obj

    # --- SQS Operations ---

    def send_job_message(self, message_body: dict) -> None:
        """Send a job message to SQS queue."""
        self.sqs.send_message(
            QueueUrl=settings.queue_url,
            MessageBody=json.dumps(message_body),
        )

    @staticmethod
    def generate_job_id() -> str:
        """Generate a new unique job ID."""
        return str(uuid.uuid4())


# Module-level singleton instance
aws = AwsService()
