# import os
# import uuid
# import json
# import time
# import boto3
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from decimal import Decimal
#
# # Import settings đã cấu hình sẵn từ file config.py
# from config import settings
#
# app = Flask(__name__)
# # Cho phép Frontend React (mọi domain) gọi API
# CORS(app)
#
# # --- KHỞI TẠO KẾT NỐI AWS ---
# session = boto3.Session(
#     aws_access_key_id=settings.aws_access_key_id,
#     aws_secret_access_key=settings.aws_secret_access_key,
#     region_name=settings.region
# )
#
# s3 = session.client('s3')
# sqs = session.client('sqs')
# dynamodb = session.resource('dynamodb')
# table = dynamodb.Table(settings.table_name)  # Tự nhận tên 'DocxJobs' từ config
#
#
# # --- API UPLOAD FILE ---
# @app.route('/api/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
#
#     file = request.files['file']
#     num_variants = request.form.get('numVariants', 10)
#
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
#
#     # 1. Tạo Job ID và đường dẫn lưu file
#     job_id = str(uuid.uuid4())
#     file_extension = os.path.splitext(file.filename)[1]
#     s3_key = f"uploads/{job_id}{file_extension}"
#     timestamp = int(time.time())
#
#     try:
#         # 2. Upload file gốc lên S3 Input
#         s3.upload_fileobj(file, settings.bucket_input, s3_key)
#
#         # 3. Ghi trạng thái 'Queued' vào DynamoDB
#         # Lưu ý: Key là 'JobId' (PascalCase) để khớp với Worker
#         table.put_item(
#             Item={
#                 'JobId': job_id,
#                 'Status': 'Queued',
#                 'FileName': file.filename,
#                 'CreatedAt': timestamp,
#                 'UpdatedAt': timestamp,
#                 'NumVariants': int(num_variants)
#             }
#         )
#
#         # 4. Gửi tin nhắn vào SQS (Worker sẽ lắng nghe cái này)
#         message_body = {
#             "jobId": job_id,  # camelCase để worker parse
#             "fileKey": s3_key,
#             "original_filename": file.filename,
#             "numVariants": int(num_variants),
#             "status": "Queued"
#         }
#
#         sqs.send_message(
#             QueueUrl=settings.queue_url,
#             MessageBody=json.dumps(message_body)
#         )
#
#         # 5. Trả kết quả ngay cho Frontend
#         return jsonify({
#             'JobId': job_id,
#             'Status': 'Queued',
#             'message': 'File uploaded successfully'
#         })
#
#     except Exception as e:
#         print(f"Error: {e}")
#         return jsonify({'error': str(e)}), 500
#
#
# # --- API KIỂM TRA TRẠNG THÁI (POLLING) ---
# @app.route('/api/status/<job_id>', methods=['GET'])
# def get_status(job_id):
#     try:
#         response = table.get_item(Key={'JobId': job_id})
#
#         if 'Item' in response:
#             item = response['Item']
#
#             # Xử lý convert Decimal của DynamoDB sang int/float để tránh lỗi JSON
#             def decimal_default(obj):
#                 if isinstance(obj, Decimal):
#                     return int(obj) if obj % 1 == 0 else float(obj)
#                 return obj
#
#             # Trả về các trường cần thiết cho Frontend
#             result = {
#                 'JobId': item.get('JobId'),
#                 'Status': item.get('Status'),
#                 'OutputUrl': item.get('OutputUrl'),  # Link tải file nếu xong
#                 'CreatedAt': decimal_default(item.get('CreatedAt', 0)),
#                 'UpdatedAt': decimal_default(item.get('UpdatedAt', 0))
#             }
#             return jsonify(result)
#         else:
#             return jsonify({'error': 'Job not found'}), 404
#
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#
#
# if __name__ == '__main__':
#     # Chạy server ở port 5000
#     app.run(host='0.0.0.0', port=5000, debug=True)
import os
import uuid
import json
import time
import boto3
from flask import Flask, request, jsonify
from flask_cors import CORS
from decimal import Decimal
from config import settings

app = Flask(__name__)
CORS(app)

# --- KHỞI TẠO AWS ---
session = boto3.Session(
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.region
)
s3 = session.client('s3')
sqs = session.client('sqs')
dynamodb = session.resource('dynamodb')
table = dynamodb.Table(settings.table_name)


# --- 1. API CẤP LINK UPLOAD (Presigned URL) ---
@app.route('/api/get-upload-url', methods=['POST'])
def get_upload_url():
    data = request.get_json()
    filename = data.get('fileName', 'unknown.docx')
    file_type = data.get('fileType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    job_id = str(uuid.uuid4())
    # Clean tên file và tạo key
    safe_name = "".join([c for c in filename if c.isalnum() or c in "._- "])
    s3_key = f"uploads/{job_id}/{safe_name}"

    try:
        # Tạo Presigned URL (cho phép Client PUT file lên S3 trong 5 phút)
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.bucket_input,
                'Key': s3_key,
                'ContentType': file_type
            },
            ExpiresIn=300  # 5 phút
        )

        # Lưu trạng thái 'Pending Upload' vào DynamoDB
        timestamp = int(time.time())
        table.put_item(
            Item={
                'JobId': job_id,
                'Status': 'PendingUpload',
                'FileName': filename,
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp
            }
        )

        return jsonify({
            'jobId': job_id,
            'uploadUrl': presigned_url,
            'fileKey': s3_key
        })

    except Exception as e:
        print(f"Error generating URL: {e}")
        return jsonify({'error': str(e)}), 500


# --- 2. API KÍCH HOẠT XỬ LÝ (Sau khi FE upload xong) ---
@app.route('/api/submit-job', methods=['POST'])
def submit_job():
    data = request.get_json()
    job_id = data.get('jobId')
    file_key = data.get('fileKey')
    num_variants = data.get('numVariants', 10)

    if not job_id or not file_key:
        return jsonify({'error': 'Missing jobId or fileKey'}), 400

    try:
        # Update trạng thái sang 'Queued'
        timestamp = int(time.time())
        table.update_item(
            Key={'JobId': job_id},
            UpdateExpression="SET #s = :status, NumVariants = :num, UpdatedAt = :ts",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={
                ':status': 'Queued',
                ':num': int(num_variants),
                ':ts': timestamp
            }
        )

        # Gửi tin nhắn cho Worker qua SQS
        # (Chuyển logic gửi SQS từ Frontend về đây -> Bảo mật hơn)
        message_body = {
            "jobId": job_id,
            "fileKey": file_key,
            "numVariants": int(num_variants),
            "status": "Queued"
        }
        sqs.send_message(
            QueueUrl=settings.queue_url,
            MessageBody=json.dumps(message_body)
        )

        return jsonify({'message': 'Job submitted successfully', 'jobId': job_id})

    except Exception as e:
        print(f"Error submitting job: {e}")
        return jsonify({'error': str(e)}), 500


# --- 3. API POLLING TRẠNG THÁI (Giữ nguyên logic cũ) ---
@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    try:
        response = table.get_item(Key={'JobId': job_id})
        if 'Item' in response:
            item = response['Item']

            # Convert Decimal
            def decimal_default(obj):
                if isinstance(obj, Decimal):
                    return int(obj) if obj % 1 == 0 else float(obj)
                return obj

            # Xử lý trường hợp chưa có OutputUrl
            result = {
                'JobId': item.get('JobId'),
                'Status': item.get('Status'),
                'OutputUrl': item.get('OutputUrl', None),
                'CreatedAt': decimal_default(item.get('CreatedAt', 0)),
                'UpdatedAt': decimal_default(item.get('UpdatedAt', 0))
            }
            return jsonify(result)
        else:
            return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)