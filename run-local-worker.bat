@echo off
setlocal

:: Cấu hình AWS (Nếu chưa set trong System Environment Variables)
:: set AWS_ACCESS_KEY_ID=YOUR_KEY
:: set AWS_SECRET_ACCESS_KEY=YOUR_SECRET
:: set AWS_REGION=ap-southeast-1

:: Cấu hình Queue
set AWS_SQS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/014197010718/docx-queue
set AWS_S3_BUCKET_INPUT=app-docx-input-team1
set AWS_S3_BUCKET_OUTPUT=app-docx-output-team1
set AWS_DYNAMODB_TABLE=DocxJobs

echo ===================================================
echo   🚀 ExamShuffling Local Worker
echo   Dang ket noi den SQS: %AWS_SQS_QUEUE_URL%
echo ===================================================

:: Kiểm tra python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python chua duoc cai dat!
    pause
    exit /b 1
)

:: Chạy worker
cd backend
echo Dang chay worker.py... (Nhan Ctrl+C de dung)
python worker.py

endlocal
pause
