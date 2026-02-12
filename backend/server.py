"""
ExamShuffling API — Thin Controller Layer.
All business logic is delegated to the services package.
"""
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from exceptions import ExamError
from schemas import (
    UploadUrlRequest, UploadUrlResponse,
    SubmitJobRequest, SubmitJobResponse,
    JobStatusResponse, PreviewResponse,
)
from services.aws_service import aws
from services.answer_parser import parse_answer_map_from_text
from services.preview_service import process_preview
from routers import debug_router

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
    version="2.0.1"
)
app.include_router(debug_router.router)

# --- METRICS ---
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 1. API CẤP LINK UPLOAD (Presigned URL) ---
@app.post("/api/get-upload-url", response_model=UploadUrlResponse)
async def get_upload_url(request: UploadUrlRequest):
    try:
        job_id = aws.generate_job_id()
        presigned_url, s3_key = aws.generate_presigned_upload_url(
            job_id, request.fileName, request.fileType
        )
        aws.create_job_record(job_id, request.fileName)

        return UploadUrlResponse(
            jobId=job_id,
            uploadUrl=presigned_url,
            fileKey=s3_key,
        )
    except Exception as e:
        logger.error(f"Error generating URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. API KÍCH HOẠT XỬ LÝ ---
@app.post("/api/submit-job", response_model=SubmitJobResponse)
async def submit_job(request: SubmitJobRequest):
    if not request.jobId or not request.fileKey:
        raise HTTPException(status_code=400, detail="Missing jobId or fileKey")

    # Parse answer map from rawText if provided
    answer_map = None
    if request.rawText:
        try:
            logger.info(f"Extracting Answer Map from RawText for job {request.jobId}...")
            answer_map = parse_answer_map_from_text(request.rawText)
            logger.info(f"Extracted {len(answer_map)} answers.")
        except Exception as e:
            logger.error(f"Failed to parse rawText for job {request.jobId}: {e}")

    try:
        aws.update_job_status(request.jobId, "Queued", num_variants=request.numVariants)

        aws.send_job_message({
            "jobId": request.jobId,
            "fileKey": request.fileKey,
            "numVariants": request.numVariants,
            "status": "Queued",
            "answerMap": answer_map,
        })

        return SubmitJobResponse(
            message="Job submitted successfully",
            jobId=request.jobId,
        )
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- 3. API POLLING TRẠNG THÁI ---
@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    try:
        item = aws.get_job_item(job_id)
        if not item:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(
            JobId=item.get('JobId'),
            Status=item.get('Status'),
            OutputUrl=item.get('OutputUrl'),
            CreatedAt=aws.decimal_convert(item.get('CreatedAt', 0)),
            UpdatedAt=aws.decimal_convert(item.get('UpdatedAt', 0)),
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
        preview_data = await process_preview(contents)

        return PreviewResponse(status="success", data=preview_data)

    except ExamError as e:
        logger.warning(f"Preview Logic Error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview Error: {str(e)}", exc_info=True)
        if "BadZipFile" in str(type(e).__name__):
            raise HTTPException(status_code=400, detail="File DOCX bị lỗi (Bad Zip). Vui lòng thử lại với file khác.")
        if "PackageNotFoundError" in str(type(e).__name__):
            raise HTTPException(status_code=400, detail="File không đúng định dạng DOCX hoặc bị hỏng.")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi xử lý file: {str(e)}")


# --- EXCEPTION HANDLERS ---
@app.exception_handler(ExamError)
async def exam_error_handler(request, exc: ExamError):  # type: ignore
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "code": exc.code}
    )


# --- MAIN ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)