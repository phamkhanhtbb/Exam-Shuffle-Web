# ExamShuffling Frontend

Hệ thống Frontend cho dự án ExamShuffling - Tự động tạo đề thi trắc nghiệm với React + TypeScript + AWS

## 🚀 Tính năng

- ✅ Upload file `.docx` lên AWS S3
- ✅ Tạo job và gửi vào SQS queue
- ✅ Theo dõi trạng thái xử lý real-time qua DynamoDB
- ✅ Download file ZIP chứa các mã đề và đáp án
- ✅ UI/UX hiện đại với drag & drop
- ✅ Responsive design

## 📋 Yêu cầu

- Node.js 16+ và npm/yarn
- AWS Account với các dịch vụ:
  - S3 (2 buckets: input và output)
  - SQS (1 queue)
  - DynamoDB (1 table)
  - IAM credentials với quyền truy cập

## 🛠️ Cài đặt

### Bước 1: Clone và cài đặt dependencies

```bash
# Clone project (hoặc tạo mới)
npm install
```

### Bước 2: Cấu hình AWS

1. Copy file `.env.example` thành `.env`:
```bash
cp .env.example .env
```

2. Điền thông tin AWS vào file `.env`:
```env
REACT_APP_AWS_REGION=ap-southeast-1
REACT_APP_AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
REACT_APP_AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY

REACT_APP_S3_BUCKET_INPUT=app-docx-input-team1
REACT_APP_S3_BUCKET_OUTPUT=app-docx-output-team1

REACT_APP_SQS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/123456789/ExamQueue

REACT_APP_DYNAMODB_TABLE=ExamShufflingJobs
```

### Bước 3: Cấu hình AWS Resources

#### 3.1 Tạo S3 Buckets

```bash
# Tạo bucket input
aws s3 mb s3://app-docx-input-team1 --region ap-southeast-1

# Tạo bucket output
aws s3 mb s3://app-docx-output-team1 --region ap-southeast-1
```

#### 3.2 Cấu hình CORS cho S3 Buckets

Tạo file `cors-config.json`:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["http://localhost:3000", "https://yourdomain.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

Áp dụng CORS:
```bash
aws s3api put-bucket-cors --bucket app-docx-input-team1 --cors-configuration file://cors-config.json
aws s3api put-bucket-cors --bucket app-docx-output-team1 --cors-configuration file://cors-config.json
```

#### 3.3 Tạo DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name ExamShufflingJobs \
  --attribute-definitions \
    AttributeName=JobId,AttributeType=S \
  --key-schema \
    AttributeName=JobId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-southeast-1
```

Thêm TTL (tự động xóa record sau 1 giờ):
```bash
aws dynamodb update-time-to-live \
  --table-name ExamShufflingJobs \
  --time-to-live-specification "Enabled=true, AttributeName=ExpiresAt" \
  --region ap-southeast-1
```

#### 3.4 Tạo SQS Queue

```bash
aws sqs create-queue \
  --queue-name ExamShufflingQueue \
  --region ap-southeast-1
```

Lấy Queue URL:
```bash
aws sqs get-queue-url --queue-name ExamShufflingQueue --region ap-southeast-1
```

#### 3.5 Cấu hình IAM Policy

Tạo policy với quyền cần thiết:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::app-docx-input-team1/*",
        "arn:aws:s3:::app-docx-output-team1/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage"
      ],
      "Resource": "arn:aws:sqs:ap-southeast-1:YOUR_ACCOUNT:ExamShufflingQueue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:ap-southeast-1:YOUR_ACCOUNT:table/ExamShufflingJobs"
    }
  ]
}
```

## 🎯 Chạy ứng dụng

### Development

```bash
npm start
```

Truy cập: http://localhost:3000

### Production Build

```bash
npm run build
```

Deploy folder `build/` lên hosting (Netlify, Vercel, S3 Static Website...)

## 📁 Cấu trúc thư mục

```
src/
├── config/
│   └── aws.ts              # Cấu hình AWS clients
├── services/
│   ├── s3Service.ts        # Upload file lên S3
│   ├── sqsService.ts       # Gửi message vào SQS
│   ├── dynamoDBService.ts  # Quản lý job status
│   └── examShufflingService.ts  # Orchestrator chính
├── components/
│   ├── FileUpload.tsx      # Component upload file
│   ├── FileUpload.css
│   ├── ProgressTracker.tsx # Hiển thị trạng thái
│   └── ProgressTracker.css
├── types/
│   └── index.ts            # TypeScript definitions
├── App.tsx                 # Component chính
├── App.css
└── index.tsx              # Entry point
```

## 🔄 Luồng hoạt động

1. **User chọn file .docx**
   - Validate file type và size
   - Hiển thị file đã chọn

2. **User nhập số lượng đề thi cần tạo**
   - Mặc định: 10 đề
   - Khoảng: 1-100 đề

3. **User click "Bắt đầu xử lý"**
   - Upload file lên S3 bucket input
   - Tạo JobId unique (UUID)
   - Tạo record trong DynamoDB với status = "Queued"
   - Gửi message vào SQS queue

4. **Backend Worker xử lý (Python)**
   - Nhận message từ SQS
   - Update status = "Processing"
   - Xử lý file, tạo các mã đề
   - Tạo file ZIP + Excel đáp án
   - Upload lên S3 bucket output
   - Update status = "Done" + OutputUrl

5. **Frontend polling status**
   - Poll DynamoDB mỗi 5 giây
   - Hiển thị progress bar
   - Khi Done → hiển thị link download

6. **User download kết quả**
   - Click button "Tải về file ZIP"
   - Download từ presigned URL

## 🔐 Bảo mật

- ⚠️ **KHÔNG** commit file `.env` lên Git
- ⚠️ **KHÔNG** hardcode credentials trong code
- ✅ Sử dụng IAM roles khi deploy lên EC2/Lambda
- ✅ Enable CORS đúng domain
- ✅ Sử dụng presigned URL với thời gian expire ngắn
- ✅ Enable CloudFront cho S3 static website

## 🐛 Debug

### Lỗi CORS
- Kiểm tra CORS configuration của S3 buckets
- Đảm bảo origin trong `.env` khớp với domain

### Lỗi AWS credentials
- Kiểm tra Access Key và Secret Key
- Đảm bảo IAM user có đủ quyền

### Job không được xử lý
- Kiểm tra Backend worker có đang chạy không
- Kiểm tra SQS queue có nhận được message không
- Xem logs trong CloudWatch

### File upload bị lỗi
- Kiểm tra file size (< 50MB)
- Kiểm tra định dạng file (.docx)
- Kiểm tra bucket name trong `.env`

## 📊 Monitoring

- **CloudWatch Logs**: Xem logs từ Backend worker
- **DynamoDB**: Xem status của các jobs
- **SQS Metrics**: Xem số lượng message trong queue
- **S3 Metrics**: Xem số lượng requests và bandwidth

## 🚀 Deploy Production

### Option 1: AWS Amplify
```bash
amplify init
amplify add hosting
amplify publish
```

### Option 2: Netlify
```bash
npm run build
netlify deploy --prod --dir=build
```

### Option 3: Vercel
```bash
vercel --prod
```

### Option 4: S3 Static Website + CloudFront
```bash
npm run build
aws s3 sync build/ s3://your-website-bucket
```

## 📝 Notes

- Presigned URL có thời gian expire mặc định 1 giờ
- DynamoDB items tự động xóa sau 1 giờ (TTL)
- Backend cần cấu hình file `.env` tương tự
- Đề nghị dùng AWS Cognito cho authentication trong production

## 🤝 Support

Nếu gặp vấn đề, hãy:
1. Kiểm tra console logs
2. Kiểm tra AWS CloudWatch
3. Xem lại file `.env`
4. Đảm bảo Backend đang chạy

---

Made with ❤️ for ExamShuffling Project
