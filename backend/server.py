import os
import uuid
import json
import time
import logging
import io
import asyncio
import zipfile
import boto3
from docx import Document
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from docx_serializer import DocxSerializer
from exceptions import ExamError, InvalidExamFormatException, AnswerKeyNotFoundError, FontError, EmptyQuestionError
from config import settings
from schemas import (
    UploadUrlRequest, UploadUrlResponse,
    SubmitJobRequest, SubmitJobResponse,
    JobStatusResponse, PreviewResponse, PreviewData
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("server")

# --- FASTAPI APP ---
app = FastAPI(
    title="ExamShuffling API",
    description="API for exam shuffling and processing",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AWS CLIENTS ---
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
@app.post("/api/get-upload-url", response_model=UploadUrlResponse)
async def get_upload_url(request: UploadUrlRequest):
    job_id = str(uuid.uuid4())
    safe_name = "".join([c for c in request.fileName if c.isalnum() or c in "._- "])
    s3_key = f"uploads/{job_id}/{safe_name}"

    try:
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.bucket_input,
                'Key': s3_key,
                'ContentType': request.fileType
            },
            ExpiresIn=300
        )

        timestamp = int(time.time())
        table.put_item(
            Item={
                'JobId': job_id,
                'Status': 'PendingUpload',
                'FileName': request.fileName,
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp
            }
        )

        return UploadUrlResponse(
            jobId=job_id,
            uploadUrl=presigned_url,
            fileKey=s3_key
        )

    except Exception as e:
        logger.error(f"Error generating URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. API KÍCH HOẠT XỬ LÝ ---
@app.post("/api/submit-job", response_model=SubmitJobResponse)
async def submit_job(request: SubmitJobRequest):
    if not request.jobId or not request.fileKey:
        raise HTTPException(status_code=400, detail="Missing jobId or fileKey")

    try:
        timestamp = int(time.time())
        table.update_item(
            Key={'JobId': request.jobId},
            UpdateExpression="SET #s = :status, NumVariants = :num, UpdatedAt = :ts",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={
                ':status': 'Queued',
                ':num': request.numVariants,
                ':ts': timestamp
            }
        )

        message_body = {
            "jobId": request.jobId,
            "fileKey": request.fileKey,
            "numVariants": request.numVariants,
            "status": "Queued"
        }
        sqs.send_message(
            QueueUrl=settings.queue_url,
            MessageBody=json.dumps(message_body)
        )

        return SubmitJobResponse(
            message="Job submitted successfully",
            jobId=request.jobId
        )

    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- 3. API POLLING TRẠNG THÁI ---
@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    try:
        response = table.get_item(Key={'JobId': job_id})
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Job not found")

        item = response['Item']

        def decimal_convert(obj):
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            return obj

        return JobStatusResponse(
            JobId=item.get('JobId'),
            Status=item.get('Status'),
            OutputUrl=item.get('OutputUrl'),
            CreatedAt=decimal_convert(item.get('CreatedAt', 0)),
            UpdatedAt=decimal_convert(item.get('UpdatedAt', 0))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 4. API PREVIEW ---
@app.post("/api/preview", response_model=PreviewResponse)
async def preview_exam(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    try:
        contents = await file.read()
        file_stream = io.BytesIO(contents)
        
        # Validation file type via python-docx
        try:
             doc = Document(file_stream)
        except Exception:
             raise HTTPException(status_code=400, detail="File không hợp lệ hoặc bị lỗi (Không phải file DOCX chuẩn)")

        serializer = DocxSerializer(doc)
        
        # Run CPU-bound serialization in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, serializer.serialize)

        return PreviewResponse(
            status="success",
            data=PreviewData(
                raw_text=result["raw_text"],
                assets_map=result["assets_map"]
            )
        )
    
    except ExamError as e:
        logger.warning(f"Preview Logic Error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview Error: {str(e)}", exc_info=True)
        # Check for specific likely errors
        if "BadZipFile" in str(type(e).__name__):
             raise HTTPException(status_code=400, detail="File DOCX bị lỗi (Bad Zip). Vui lòng thử lại với file khác.")
        if "PackageNotFoundError" in str(type(e).__name__):
             raise HTTPException(status_code=400, detail="File không đúng định dạng DOCX hoặc bị hỏng.")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi xử lý file: {str(e)}")


# --- EXCEPTION HANDLERS ---
@app.exception_handler(ExamError)
async def exam_error_handler(request, exc: ExamError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "code": exc.code}
    )



# --- MAIN ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)