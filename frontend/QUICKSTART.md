# 🚀 HƯỚNG DẪN CÀI ĐẶT NHANH

## Bước 1: Giải nén và cài đặt

```bash
# Giải nén file
tar -xzf exam-shuffling-frontend.tar.gz
cd exam-shuffling-frontend

# Cài đặt dependencies
npm install
```

## Bước 2: Setup AWS Resources (Tự động)

```bash
# Chạy script tự động (yêu cầu AWS CLI đã cài đặt và cấu hình)
chmod +x setup-aws.sh
./setup-aws.sh
```

Script sẽ tự động tạo:
- ✅ S3 Buckets (input + output)
- ✅ SQS Queue
- ✅ DynamoDB Table
- ✅ File .env với thông tin resources

## Bước 3: Cấu hình AWS Credentials

Mở file `.env` và điền thông tin:

```env
REACT_APP_AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
REACT_APP_AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
```

### Cách lấy Access Key:

1. Đăng nhập AWS Console
2. IAM → Users → [Your User] → Security credentials
3. Create access key → Application running outside AWS
4. Copy Access Key ID và Secret Access Key

### Quyền cần thiết:

- `s3:PutObject`, `s3:GetObject` cho 2 buckets
- `sqs:SendMessage` cho queue
- `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` cho table

## Bước 4: Setup Backend (Python Worker)

Backend cần có file `.env` tương tự:

```env
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY

AWS_SQS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/ACCOUNT_ID/ExamShufflingQueue
AWS_DYNAMODB_TABLE=ExamShufflingJobs
AWS_S3_BUCKET_INPUT=app-docx-input-team1
AWS_S3_BUCKET_OUTPUT=app-docx-output-team1

VISIBILITY_TIMEOUT=120
HEARTBEAT_SECONDS=30
MAX_ATTEMPTS=5
PRESIGN_EXPIRES_IN=3600
```

Chạy worker:
```bash
cd backend
pip install -r requirements.txt
python worker.py
```

## Bước 5: Chạy Frontend

```bash
# Development
npm start

# Production build
npm run build
```

Mở trình duyệt: http://localhost:3000

## 🎯 Kiểm tra hoạt động

1. Upload file `.docx` template
2. Chọn số lượng đề (VD: 10 đề)
3. Click "Bắt đầu xử lý"
4. Đợi xử lý hoàn tất (~30s cho 10 đề)
5. Download file ZIP chứa kết quả

## 🐛 Troubleshooting

### Lỗi: "Network error" hoặc "CORS"
→ Kiểm tra CORS configuration của S3 buckets
→ Chạy lại: `./setup-aws.sh`

### Lỗi: "Access Denied"
→ Kiểm tra IAM permissions
→ Đảm bảo user có quyền truy cập S3, SQS, DynamoDB

### Job không được xử lý
→ Kiểm tra Backend worker có đang chạy không
→ Xem logs: `python worker.py`

### File upload nhưng không có kết quả
→ Kiểm tra DynamoDB table
→ Kiểm tra SQS queue (có message không?)
→ Xem CloudWatch logs

## 📞 Support

Nếu gặp vấn đề:
1. Kiểm tra Console logs (F12)
2. Kiểm tra file `.env` đã đúng chưa
3. Đảm bảo Backend đang chạy
4. Xem AWS CloudWatch logs

---

**Lưu ý quan trọng:**
- ⚠️ KHÔNG commit file `.env` lên Git
- ⚠️ Sử dụng IAM roles thay vì hardcode credentials trong production
- ⚠️ Enable CloudFront cho S3 static website trong production
