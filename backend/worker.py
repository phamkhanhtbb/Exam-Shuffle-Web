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

# Import các module đã tách
from config import load_settings
from docx_processor import process_exam_batch

# 1. Setup & Cấu hình
SETTINGS = load_settings()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("worker")

# Biến global cho multiprocessing (sẽ được khởi tạo trong từng process con)
sqs = None
s3 = None
dynamodb = None
table = None
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"


def _parse_sqs_body(message: Dict[str, Any]) -> Tuple[str, str, Dict[str, str], Optional[List[int]], int]:
    """Parse message body từ SQS, lấy thông tin job."""
    raw_body = message.get('Body')
    if not raw_body:
        raise ValueError("Message không có Body")

    body = json.loads(raw_body)
    job_id = body.get('jobId')
    file_key = body.get('fileKey')
    permutation = body.get('permutation')

    # Lấy số lượng đề, mặc định là 1
    num_variants = body.get('numVariants', 1)
    if not isinstance(num_variants, int) or num_variants < 1:
        num_variants = 1

    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("jobId không hợp lệ")
    if not isinstance(file_key, str) or not file_key.strip():
        raise ValueError("fileKey không hợp lệ")

    perm_list: Optional[List[int]] = None
    if permutation is not None:
        if isinstance(permutation, list) and all(isinstance(x, int) for x in permutation):
            perm_list = [int(x) for x in permutation]

    return job_id.strip(), file_key.strip(), perm_list, num_variants


def _safe_output_key(job_id: str, input_file_key: str) -> str:
    """Luôn trả về file .zip vì giờ hệ thống xử lý theo batch."""
    return f"result_{job_id}.zip"


def _mark_processing(job_id: str) -> bool:
    """Đánh dấu job đang xử lý trong DynamoDB (Optimistic Locking)."""
    try:
        table.update_item(
            Key={'JobId': job_id},
            UpdateExpression="SET #s = :processing, WorkerId = :wid, UpdatedAt = :ts",
            ConditionExpression="attribute_not_exists(#s) OR #s IN (:queued, :failed)",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={
                ':processing': 'Processing',
                ':queued': 'Queued',
                ':failed': 'Failed',
                ':wid': WORKER_ID,
                ':ts': int(time.time()),
            },
        )
        return True
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code')
        if code == 'ConditionalCheckFailedException':
            return False
        raise


def _mark_done(job_id: str, output_url: str, output_key: str) -> None:
    """Cập nhật trạng thái Done và lưu link tải."""
    ttl_timestamp = int(time.time()) + 3600  # Link hết hạn sau 1 giờ
    table.update_item(
        Key={'JobId': job_id},
        UpdateExpression="SET #s = :done, OutputUrl = :url, OutputKey = :okey, UpdatedAt = :ts, ExpiresAt = :ttl",
        ExpressionAttributeNames={'#s': 'Status'},
        ExpressionAttributeValues={
            ':done': 'Done',
            ':url': output_url,
            ':okey': output_key,
            ':ts': int(time.time()),
            ':ttl': ttl_timestamp,
        },
    )


def _mark_failed(job_id: str, error_message: str) -> None:
    """Cập nhật trạng thái Failed."""
    msg = (error_message or "")[:800]
    try:
        table.update_item(
            Key={'JobId': job_id},
            UpdateExpression="SET #s = :failed, LastError = :err, UpdatedAt = :ts",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={
                ':failed': 'Failed',
                ':err': msg,
                ':ts': int(time.time()),
            },
        )
    except Exception as e:
        logger.error(f"Không thể update trạng thái failed cho job {job_id}: {e}")


def _should_retry(exc: Exception) -> bool:
    """Quyết định có retry message hay không dựa trên loại lỗi."""
    if isinstance(exc, (ValueError, json.JSONDecodeError)):
        return False
    if isinstance(exc, (BotoCoreError,)):
        return True
    if isinstance(exc, ClientError):
        code = exc.response.get('Error', {}).get('Code', '')
        retryable = {'ProvisionedThroughputExceededException', 'ThrottlingException', 'RequestLimitExceeded',
                     'SlowDown', 'InternalError', 'ServiceUnavailable'}
        return code in retryable
    return True


def _start_visibility_heartbeat(receipt_handle: str, stop_event: threading.Event) -> threading.Thread:
    """Gia hạn Visibility Timeout định kỳ để tránh job bị SQS đẩy lại."""

    def _run() -> None:
        while not stop_event.wait(SETTINGS.heartbeat_seconds):
            try:
                sqs.change_message_visibility(
                    QueueUrl=SETTINGS.queue_url,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=SETTINGS.visibility_timeout,
                )
                # Health Check point (Optional)
                # with open("/tmp/heartbeat", "w") as f: f.write(str(time.time()))
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    t = threading.Thread(target=_run, name="visibility-heartbeat", daemon=True)
    t.start()
    return t


def process_message() -> None:
    """Hàm xử lý chính cho từng message."""
    logger.info("Đang chờ tin nhắn...")

    try:
        response = sqs.receive_message(
            QueueUrl=SETTINGS.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=SETTINGS.visibility_timeout,
            AttributeNames=['All'],
        )
    except Exception as e:
        logger.error(f"Lỗi kết nối SQS: {e}")
        time.sleep(5)
        return

    if 'Messages' not in response:
        return

    message = response['Messages'][0]
    receipt_handle = message['ReceiptHandle']
    attrs = message.get('Attributes') or {}
    receive_count = int(attrs.get('ApproximateReceiveCount', '1'))

    job_id: Optional[str] = None
    started_at = time.time()

    try:
        # 1. Parse thông tin job
        job_id, file_key, permutation, num_variants = _parse_sqs_body(message)
        logger.info(f"JOB: {job_id} | File: {file_key} | Variants: {num_variants} | Attempt: {receive_count}")

        # 2. Kiểm tra số lần retry
        if receive_count >= SETTINGS.max_attempts:
            _mark_failed(job_id, f"Vượt quá số lần retry ({receive_count}/{SETTINGS.max_attempts}).")
            sqs.delete_message(QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle)
            return

        # 3. Lock job trong DynamoDB
        locked = _mark_processing(job_id)
        if not locked:
            logger.info(f"Job {job_id} đang được xử lý bởi worker khác hoặc đã hoàn thành.")
            sqs.delete_message(QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle)
            return

        # 4. Định nghĩa Heartbeat Callback
        def heartbeat_callback():
            """Hàm này sẽ được gọi từ bên trong vòng lặp xử lý file để gia hạn thời gian"""
            try:
                sqs.change_message_visibility(
                    QueueUrl=SETTINGS.queue_url,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=SETTINGS.visibility_timeout
                )
            except Exception as hb_err:
                logger.warning(f"Heartbeat failed: {hb_err}")

        # 5. Xử lý file trong môi trường tạm (Disk I/O)
        with tempfile.TemporaryDirectory(prefix=f"job_{job_id}_") as tmpdir:
            local_input_path = os.path.join(tmpdir, "input.docx")
            local_output_path = os.path.join(tmpdir, "result.zip")

            # Download từ S3
            logger.info(f"Download s3://{SETTINGS.bucket_input}/{file_key}")
            s3.download_file(SETTINGS.bucket_input, file_key, local_input_path)

            with open(local_input_path, "rb") as f:
                source_bytes = f.read()

            # --- GỌI MODULE XỬ LÝ ---
            # Truyền đường dẫn file output và callback
            process_exam_batch(
                source_bytes=source_bytes,
                job_id=job_id,
                num_variants=num_variants,
                output_zip_path=local_output_path,
                progress_callback=heartbeat_callback
            )

            # Upload ZIP lên S3 Output
            # FIX: Thêm ExtraArgs ở đây để set ContentType metadata cho file trên S3
            output_key = _safe_output_key(job_id, file_key)
            logger.info(f"Upload ZIP lên S3: s3://{SETTINGS.bucket_output}/{output_key}")

            s3.upload_file(
                local_output_path,
                SETTINGS.bucket_output,
                output_key,
                ExtraArgs={'ContentType': 'application/zip'}
            )

        # 6. Tạo link tải (Presigned URL)
        # FIX: Không cần ExtraArgs ở đây nữa vì file trên S3 đã có metadata đúng
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': SETTINGS.bucket_output, 'Key': output_key},
            ExpiresIn=SETTINGS.presign_expires_in
        )

        # 7. Hoàn tất
        _mark_done(job_id, presigned_url, output_key)
        sqs.delete_message(QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle)

        elapsed_ms = int((time.time() - started_at) * 1000)
        logger.info(f"Hoàn tất job: {job_id} trong {elapsed_ms}ms")

    except Exception as e:
        logger.exception(f"Lỗi job {job_id}: {e}")
        if job_id:
            _mark_failed(job_id, str(e))

        # Quyết định retry hay xóa message
        if not _should_retry(e):
            logger.info(f"Lỗi không thể retry, xóa message job {job_id}.")
            sqs.delete_message(QueueUrl=SETTINGS.queue_url, ReceiptHandle=receipt_handle)
    finally:
        # Không cần dọn dẹp thread nữa
        pass

def run_worker_process(worker_num: int) -> None:
    """Hàm khởi chạy cho mỗi process con."""
    global sqs, s3, dynamodb, table

    # Khởi tạo client boto3 trong từng process (best practice cho multiprocessing)
    # Reload settings để đảm bảo biến môi trường cập nhật nếu cần
    settings = load_settings()

    sqs = boto3.client('sqs', region_name=settings.region)
    s3 = boto3.client('s3', region_name=settings.region)
    dynamodb = boto3.resource('dynamodb', region_name=settings.region)
    table = dynamodb.Table(settings.table_name)

    logger.info(f"Process-{worker_num} (PID: {os.getpid()}) khởi động.")

    while True:
        try:
            process_message()
        except Exception as e:
            logger.error(f"Process-{worker_num} crash vòng lặp chính: {e}")
            time.sleep(5)


if __name__ == "__main__":
    # Tự động điều chỉnh số lượng worker theo CPU
    cpu_count = multiprocessing.cpu_count()
    NUM_WORKERS = max(2, cpu_count)

    processes = []
    print(f"--- BẮT ĐẦU CHẠY {NUM_WORKERS} WORKER PROCESSES  ---")

    for i in range(NUM_WORKERS):
        p = multiprocessing.Process(target=run_worker_process, args=(i + 1,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()