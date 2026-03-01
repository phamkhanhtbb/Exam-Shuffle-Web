"""
Background Worker for Exam Processing.

This module listens for messages from an AWS SQS queue, downloads DOCX templates
from S3, processes them (generating multiple variants), uploads the results
back to S3, and updates the job status in DynamoDB.

It uses Python's multiprocessing to run multiple workers in parallel,
maximizing CPU utilization for document generation.
"""

import boto3
import json
import os
import logging
import socket
import tempfile
import threading
import time
import multiprocessing
from typing import Any, Dict, Optional, Tuple, List

from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config

# Local imports for configuration and processing logic.
from config import load_settings
from docx_processor import process_exam_batch

# -- 1. Configuration & Logging --
SETTINGS = load_settings()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("worker")

# Global variables for AWS clients (initialized per worker process).
sqs = None
s3 = None
dynamodb = None
table = None

# Unique identifier for this specific worker instance (Host:PID).
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"


def _parse_sqs_body(
    message: Dict[str, Any],
) -> Tuple[str, str, Optional[List[int]], int, Optional[dict], Optional[str]]:
    """
    Extracts job details from the SQS message body.
    Expected fields: jobId, fileKey, numVariants, answerMap, examCodes.
    """
    raw_body = message.get("Body")
    if not raw_body:
        raise ValueError("Message body is missing")

    body = json.loads(raw_body)
    job_id = body.get("jobId")
    file_key = body.get("fileKey")
    permutation = body.get("permutation")
    answer_map = body.get("answerMap")
    exam_codes = body.get("examCodes")

    # Default to 1 variant if not specified.
    num_variants = body.get("numVariants", 1)
    if not isinstance(num_variants, int) or num_variants < 1:
        num_variants = 1

    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("Invalid jobId")
    if not isinstance(file_key, str) or not file_key.strip():
        raise ValueError("Invalid fileKey")

    perm_list: Optional[List[int]] = None
    if permutation is not None:
        if isinstance(permutation, list) and all(
            isinstance(x, int) for x in permutation
        ):
            perm_list = [int(x) for x in permutation]

    return (
        job_id.strip(),
        file_key.strip(),
        perm_list,
        num_variants,
        answer_map,
        exam_codes,
    )


def _safe_output_key(job_id: str, input_file_key: str) -> str:
    """Generates a standardized S3 key for the output ZIP file."""
    return f"result_{job_id}.zip"


def _mark_processing(job_id: str) -> bool:
    """
    Updates the job status to 'Processing' in DynamoDB.
    Uses 'Optimistic Locking' (ConditionExpression) to ensure only
    one worker processes a specific job at a time.
    """
    try:
        table.update_item(
            Key={"JobId": job_id},
            UpdateExpression="SET #s = :processing, WorkerId = :wid, UpdatedAt = :ts, JobProgress = :prog",
            ConditionExpression="attribute_not_exists(#s) OR #s IN (:queued, :failed)",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={
                ":processing": "Processing",
                ":queued": "Queued",
                ":failed": "Failed",
                ":wid": WORKER_ID,
                ":ts": int(time.time()),
                ":prog": 0,
            },
        )
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return False
        raise


def _mark_done(job_id: str, output_url: str, output_key: str) -> None:
    """
    Updates the job status to 'Done' and stores the download URL.
    Sets an 'ExpiresAt' timestamp for automatic TTL cleanup in DynamoDB.
    """
    ttl_timestamp = int(time.time()) + 3600  # Results valid for 1 hour.
    table.update_item(
        Key={"JobId": job_id},
        UpdateExpression="SET #s = :done, OutputUrl = :url, OutputKey = :okey, UpdatedAt = :ts, ExpiresAt = :ttl",
        ExpressionAttributeNames={"#s": "Status"},
        ExpressionAttributeValues={
            ":done": "Done",
            ":url": output_url,
            ":okey": output_key,
            ":ts": int(time.time()),
            ":ttl": ttl_timestamp,
        },
    )


def _mark_failed(job_id: str, error_message: str) -> None:
    """Sets job status to 'Failed' and logs the error message."""
    msg = (error_message or "")[:800]
    try:
        table.update_item(
            Key={"JobId": job_id},
            UpdateExpression="SET #s = :failed, LastError = :err, UpdatedAt = :ts",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={
                ":failed": "Failed",
                ":err": msg,
                ":ts": int(time.time()),
            },
        )
    except Exception as e:
        logger.error(f"Failed to update status to 'Failed' for job {job_id}: {e}")


def _should_retry(exc: Exception) -> bool:
    """
    Determines if an SQS message should be retried or discarded
    based on the nature of the error (e.g., transient network issues vs. bad input).
    """
    if isinstance(exc, (ValueError, json.JSONDecodeError)):
        return False  # Don't retry invalid data.
    if isinstance(exc, (BotoCoreError,)):
        return True
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        retryable = {
            "ProvisionedThroughputExceededException",
            "ThrottlingException",
            "RequestLimitExceeded",
            "SlowDown",
            "InternalError",
            "ServiceUnavailable",
        }
        return code in retryable
    return True


def _start_visibility_heartbeat(
    receipt_handle: str, stop_event: threading.Event
) -> threading.Thread:
    """
    Background thread to periodically extend the SQS Visibility Timeout.
    This prevents SQS from returning the message to the queue while
    it is still being processed by this worker.
    """

    def _run() -> None:
        while not stop_event.wait(SETTINGS.heartbeat_seconds):
            try:
                sqs.change_message_visibility(
                    QueueUrl=SETTINGS.queue_url,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=SETTINGS.visibility_timeout,
                )
            except Exception as e:
                logger.warning(f"Visibility heartbeat extension failed: {e}")

    t = threading.Thread(target=_run, name="visibility-heartbeat", daemon=True)
    t.start()
    return t


def process_message() -> None:
    """
    The main processing loop for a single worker:
    1. Wait for a message from SQS (Long Polling).
    2. Lock the job in DynamoDB.
    3. Download the DOCX template from S3.
    4. Call the processor to generate exam variants and a ZIP archive.
    5. Upload the ZIP to S3 and generate a presigned download URL.
    6. Mark job as 'Done' and delete the SQS message.
    """
    logger.info("Worker waiting for messages...")

    try:
        # Long poll for a single message.
        response = sqs.receive_message(
            QueueUrl=SETTINGS.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=SETTINGS.visibility_timeout,
            AttributeNames=["All"],
        )
    except Exception as e:
        logger.error(f"SQS connection error: {e}")
        time.sleep(5)
        return

    if "Messages" not in response:
        return

    message = response["Messages"][0]
    receipt_handle = message["ReceiptHandle"]
    attrs = message.get("Attributes") or {}
    receive_count = int(attrs.get("ApproximateReceiveCount", "1"))

    job_id: Optional[str] = None
    started_at = time.time()

    try:
        # Step 1: Parse job parameters.
        job_id, file_key, permutation, num_variants, answer_map, exam_codes = (
            _parse_sqs_body(message)
        )
        logger.info(
            f"PROCESSING JOB: {job_id} | Variants: {num_variants} | Attempt: {receive_count}"
        )

        # Step 2: Check retry limits.
        if receive_count >= SETTINGS.max_attempts:
            _mark_failed(job_id, f"Exceeded max retry attempts ({receive_count}).")
            sqs.delete_message(
                QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle
            )
            return

        # Step 3: Attempt to lock the job (Status transition to 'Processing').
        if not _mark_processing(job_id):
            logger.info(f"Job {job_id} already being processed or finished.")
            sqs.delete_message(
                QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle
            )
            return

        # Step 4: Define a heartbeat callback to keep the SQS message alive during long tasks.
        last_hb_time = [time.time()]
        from services.aws_service import aws

        def heartbeat_callback(progress_pct: int = 0):
            try:
                now = time.time()
                # Cập nhật DynamoDB tiến độ thay vì chỉ kéo dài heartbeat
                # Gọi AWS/DB max ~1.5s/lần để tránh bị block quá tải (Throttled)
                if progress_pct == 100 or now - last_hb_time[0] >= 1.0:
                    aws.update_job_status(job_id, "Processing", num_variants=num_variants, progress=progress_pct)
                    sqs.change_message_visibility(
                        QueueUrl=SETTINGS.queue_url,
                        ReceiptHandle=receipt_handle,
                        VisibilityTimeout=SETTINGS.visibility_timeout,
                    )
                    last_hb_time[0] = now
            except Exception as hb_err:
                logger.warning(f"In-process heartbeat failed: {hb_err}")

        # Step 5: Perform processing within a temporary directory for safe local storage.
        with tempfile.TemporaryDirectory(prefix=f"job_{job_id}_") as tmpdir:
            local_input_path = os.path.join(tmpdir, "input.docx")
            local_output_path = os.path.join(tmpdir, "result.zip")

            # Download template from S3.
            s3.download_file(SETTINGS.bucket_input, file_key, local_input_path)

            with open(local_input_path, "rb") as f:
                source_bytes = f.read()

            # --- EXECUTE EXAM GENERATION ---
            # This handles structure parsing, randomization, and ZIP creation.
            process_exam_batch(
                source_bytes=source_bytes,
                job_id=job_id,
                num_variants=num_variants,
                output_zip_path=local_output_path,
                progress_callback=heartbeat_callback,
                external_answer_map=answer_map,
                exam_codes_str=exam_codes,
            )

            # Upload the resulting ZIP file to S3.
            output_key = _safe_output_key(job_id, file_key)
            s3.upload_file(
                local_output_path,
                SETTINGS.bucket_output,
                output_key,
                ExtraArgs={"ContentType": "application/zip"},
            )

        # Step 6: Generate a presigned URL so the user can download the result directly.
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": SETTINGS.bucket_output, "Key": output_key},
            ExpiresIn=SETTINGS.presign_expires_in,
        )

        # Step 7: Finalize job and cleanup SQS.
        _mark_done(job_id, presigned_url, output_key)
        sqs.delete_message(QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle)

        elapsed_ms = int((time.time() - started_at) * 1000)
        logger.info(f"JOB COMPLETED: {job_id} in {elapsed_ms}ms")

    except Exception as e:
        logger.exception(f"Error processing job {job_id}: {e}")
        if job_id:
            _mark_failed(job_id, str(e))

        # Handle retries vs. deletion.
        if not _should_retry(e):
            logger.info(f"Non-retryable error, deleting message for job {job_id}.")
            sqs.delete_message(
                QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle
            )
    finally:
        pass


def run_worker_process(worker_num: int) -> None:
    """
    Entry point for a child process.
    Initializes dedicated AWS clients for the process to avoid thread-safety issues.
    """
    global sqs, s3, dynamodb, table

    # Load fresh settings for the new process environment.
    settings = load_settings()

    # Explicitly disable proxies to ensure direct AWS connectivity.
    my_config = Config(region_name=settings.region, proxies={})

    sqs = boto3.client("sqs", config=my_config)
    s3 = boto3.client("s3", config=my_config)
    dynamodb = boto3.resource("dynamodb", config=my_config)
    table = dynamodb.Table(settings.table_name)

    logger.info(f"Worker Process-{worker_num} (PID: {os.getpid()}) started.")

    # Continuously pull and process messages.
    while True:
        try:
            process_message()
        except Exception as e:
            logger.error(f"Worker Process-{worker_num} main loop crash: {e}")
            time.sleep(5)


if __name__ == "__main__":
    """
    Main Launcher: Starts multiple worker processes based on the available CPU count.
    """
    cpu_count = multiprocessing.cpu_count()
    NUM_WORKERS = max(2, cpu_count)

    processes = []
    print(f"--- STARTING {NUM_WORKERS} WORKER PROCESSES ---")

    for i in range(NUM_WORKERS):
        p = multiprocessing.Process(target=run_worker_process, args=(i + 1,))
        p.start()
        processes.append(p)

    # Wait for all processes to finish (normally they run indefinitely).
    for p in processes:
        p.join()
