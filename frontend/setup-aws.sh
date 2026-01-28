#!/bin/bash

# Script tự động setup AWS resources cho ExamShuffling
# Chạy: chmod +x setup-aws.sh && ./setup-aws.sh

set -e

echo "🚀 ExamShuffling AWS Setup Script"
echo "=================================="
echo ""

# Cấu hình
REGION="ap-southeast-1"
BUCKET_INPUT="app-docx-input-team1"
BUCKET_OUTPUT="app-docx-output-team1"
QUEUE_NAME="ExamShufflingQueue"
TABLE_NAME="ExamShufflingJobs"

# Màu sắc
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📍 Region: ${REGION}${NC}"
echo ""

# 1. Tạo S3 Buckets
echo "📦 Step 1/5: Tạo S3 Buckets..."
echo ""

echo "  → Tạo bucket input: ${BUCKET_INPUT}"
aws s3 mb s3://${BUCKET_INPUT} --region ${REGION} 2>/dev/null || echo "  Bucket đã tồn tại"

echo "  → Tạo bucket output: ${BUCKET_OUTPUT}"
aws s3 mb s3://${BUCKET_OUTPUT} --region ${REGION} 2>/dev/null || echo "  Bucket đã tồn tại"

echo -e "${GREEN}✅ S3 Buckets created${NC}"
echo ""

# 2. Cấu hình CORS cho S3
echo "🌐 Step 2/5: Cấu hình CORS cho S3..."
echo ""

cat > /tmp/cors-config.json <<EOF
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["http://localhost:3000", "*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
EOF

echo "  → Applying CORS to ${BUCKET_INPUT}"
aws s3api put-bucket-cors --bucket ${BUCKET_INPUT} --cors-configuration file:///tmp/cors-config.json

echo "  → Applying CORS to ${BUCKET_OUTPUT}"
aws s3api put-bucket-cors --bucket ${BUCKET_OUTPUT} --cors-configuration file:///tmp/cors-config.json

rm /tmp/cors-config.json
echo -e "${GREEN}✅ CORS configured${NC}"
echo ""

# 3. Tạo DynamoDB Table
echo "💾 Step 3/5: Tạo DynamoDB Table..."
echo ""

aws dynamodb create-table \
  --table-name ${TABLE_NAME} \
  --attribute-definitions \
    AttributeName=JobId,AttributeType=S \
  --key-schema \
    AttributeName=JobId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ${REGION} 2>/dev/null || echo "  Table đã tồn tại"

echo "  → Waiting for table to be active..."
aws dynamodb wait table-exists --table-name ${TABLE_NAME} --region ${REGION}

echo "  → Enabling TTL..."
aws dynamodb update-time-to-live \
  --table-name ${TABLE_NAME} \
  --time-to-live-specification "Enabled=true, AttributeName=ExpiresAt" \
  --region ${REGION} 2>/dev/null || echo "  TTL đã được enable"

echo -e "${GREEN}✅ DynamoDB Table created${NC}"
echo ""

# 4. Tạo SQS Queue
echo "📨 Step 4/5: Tạo SQS Queue..."
echo ""

QUEUE_URL=$(aws sqs create-queue \
  --queue-name ${QUEUE_NAME} \
  --region ${REGION} \
  --query 'QueueUrl' \
  --output text 2>/dev/null || aws sqs get-queue-url \
  --queue-name ${QUEUE_NAME} \
  --region ${REGION} \
  --query 'QueueUrl' \
  --output text)

echo "  Queue URL: ${QUEUE_URL}"
echo -e "${GREEN}✅ SQS Queue created${NC}"
echo ""

# 5. Tạo file .env
echo "📝 Step 5/5: Tạo file .env..."
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > .env <<EOF
# AWS Configuration
REACT_APP_AWS_REGION=${REGION}
REACT_APP_AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_HERE
REACT_APP_AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY_HERE

# S3 Buckets
REACT_APP_S3_BUCKET_INPUT=${BUCKET_INPUT}
REACT_APP_S3_BUCKET_OUTPUT=${BUCKET_OUTPUT}

# SQS
REACT_APP_SQS_QUEUE_URL=${QUEUE_URL}

# DynamoDB
REACT_APP_DYNAMODB_TABLE=${TABLE_NAME}

# Presigned URL expiration (seconds)
REACT_APP_PRESIGN_EXPIRES_IN=3600
EOF

echo -e "${GREEN}✅ File .env created${NC}"
echo ""

# Tóm tắt
echo "=================================="
echo -e "${GREEN}🎉 Setup hoàn tất!${NC}"
echo "=================================="
echo ""
echo "📋 Tóm tắt resources:"
echo "  • S3 Input Bucket: ${BUCKET_INPUT}"
echo "  • S3 Output Bucket: ${BUCKET_OUTPUT}"
echo "  • SQS Queue: ${QUEUE_NAME}"
echo "  • DynamoDB Table: ${TABLE_NAME}"
echo "  • AWS Account ID: ${ACCOUNT_ID}"
echo ""
echo -e "${YELLOW}⚠️  Lưu ý:${NC}"
echo "  1. Vui lòng cập nhật AWS credentials trong file .env"
echo "  2. Đảm bảo IAM user có đủ quyền truy cập các resources"
echo "  3. Cấu hình Backend với cùng thông tin AWS"
echo ""
echo -e "${GREEN}Tiếp theo:${NC}"
echo "  npm install"
echo "  # Cập nhật .env với credentials"
echo "  npm start"
echo ""
