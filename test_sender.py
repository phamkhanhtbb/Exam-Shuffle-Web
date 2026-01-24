import boto3
import json
import os
import uuid
from dotenv import load_dotenv

# 1. Load cấu hình (dùng chung file .env với worker)
load_dotenv()

queue_url = os.getenv('AWS_SQS_QUEUE_URL')
region = os.getenv('AWS_REGION')

sqs = boto3.client('sqs', region_name=region)


def send_100_jobs():
    print(f"Bắt đầu gửi 100 job vào hàng đợi: {queue_url}...")

    # Giả lập dữ liệu cho 100 user khác nhau
    for i in range(1, 1000 + 1):
        job_id = f"TEST-LIVE-{i:03d}"  # Tạo ID: TEST-LIVE-001 -> TEST-LIVE-100

        # Nội dung 1 message (Đúng chuẩn JSON Object, KHÔNG PHẢI LIST)
        message_body = {
            "jobId": job_id,
            "fileKey": "template.docx",  # Đảm bảo file này đã có trên S3 Input
            "replacements": {
                "{{NAME}}": f"User Test {i}",
                "{{ORDER_ID}}": str(uuid.uuid4())[:8]
            }
        }

        try:
            response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body)  # Chuyển dict thành string JSON
            )
            print(f"[OK] Đã gửi Job {i}: {job_id} - MsgID: {response.get('MessageId')}")
        except Exception as e:
            print(f"[ERR] Lỗi gửi Job {i}: {e}")

    print("\n--- HOÀN TẤT GỬI 100 JOB ---")


if __name__ == "__main__":
    if not queue_url:
        print("Lỗi: Chưa cấu hình AWS_SQS_QUEUE_URL trong file .env")
    else:
        send_100_jobs()