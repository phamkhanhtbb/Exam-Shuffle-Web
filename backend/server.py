"""
ExamShuffling API — Thin Controller Layer.
This file handles the API endpoints, middleware setup, and delegates
complex tasks to dedicated service modules.
"""

import asyncio
import json
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from exceptions import ExamError
from schemas import (
    UploadUrlRequest,
    UploadUrlResponse,
    SubmitJobRequest,
    SubmitJobResponse,
    JobStatusResponse,
    PreviewResponse,
)
from services.aws_service import aws
from services.answer_parser import parse_answer_map_from_text
from services.preview_service import process_preview
from routers import debug_router

# -- 1. Logging Setup --
# We configure logging to track events, errors, and information about
# incoming requests and system performance.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("server")

# -- 2. FastAPI Application Initialization --
# Initialize the main FastAPI application with metadata.
app = FastAPI(
    title="ExamShuffling API",
    description="API for exam shuffling and processing",
    version="2.0.1",
)

# Include debug roots for troubleshooting purposes.
app.include_router(debug_router.router)

# -- 3. Monitoring (Metrics) --
# Expose a /metrics endpoint for Prometheus to monitor application health
# and performance metrics.
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# -- 4. CORS Middleware Configuration --
# Define which origins (websites) are allowed to make requests to this API.
# This prevents unauthorized cross-origin requests.
origins = [
    "http://localhost:3000",  # Local development (React)
    "http://localhost:3001",  # Local development (Next.js landing)
    "http://localhost",  # Local server
    "https://trondeonline.me",  # Production domain
    "https://app.trondeonline.me",  # Production SPA (subdomain)
    "https://www.trondeonline.me",  # Production domain (www)
    "https://exam-shuffle-web.vercel.app",  # Vercel preview deployment
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# -- 5. API Endpoints --


# 5.0 Endpoint: Health Check
# Lightweight endpoint for Docker healthcheck and load balancer probes.
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# 5.1 Endpoint: Get S3 Presigned Upload URL
# Step 1: User requests a link to upload their DOCX file directly to S3.
# Step 2: Server checks if the file is a valid .docx.
# Step 3: Server generates a unique Job ID and an S3 Presigned URL.
# Step 4: Server creates a record in the database (DynamoDB) for this new job.
@app.post("/api/get-upload-url", response_model=UploadUrlResponse)
async def get_upload_url(request: UploadUrlRequest):
    if not request.fileName.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

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
        logger.error(f"Error generating Upload URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 5.2 Endpoint: Submit Job for Processing
# Step 1: After uploading to S3, the user calls this API to start the processing.
# Step 2: If a raw text version of the answer key is provided, the server attempts to parse it.
# Step 3: Server updates the job status to "Queued" in the database.
# Step 4: Server sends a message to the SQS queue to be picked up by a worker process.
@app.post("/api/submit-job", response_model=SubmitJobResponse)
async def submit_job(request: SubmitJobRequest):
    if not request.jobId or not request.fileKey:
        raise HTTPException(status_code=400, detail="Missing jobId or fileKey")

    answer_map = None
    if request.rawText:
        try:
            logger.info(f"Extracting Answer Map from text for job {request.jobId}...")
            # Delegate parsing of answer keys from raw text to the service layer.
            answer_map = parse_answer_map_from_text(request.rawText)
            logger.info(f"Extracted {len(answer_map)} answers.")
        except Exception as e:
            logger.error(f"Failed to parse rawText for job {request.jobId}: {e}")

    try:
        # Update DynamoDB record.
        aws.update_job_status(request.jobId, "Queued", num_variants=request.numVariants)

        # Send processing instructions to SQS.
        aws.send_job_message(
            {
                "jobId": request.jobId,
                "fileKey": request.fileKey,
                "numVariants": request.numVariants,
                "status": "Queued",
                "answerMap": answer_map,
                "examCodes": request.examCodes,
            }
        )

        return SubmitJobResponse(
            message="Job submitted successfully",
            jobId=request.jobId,
        )
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 5.3 Endpoint: Poll Job Status (kept for backward compatibility)
# Step 1: Frontend repeatedly calls this to check if the job is finished.
# Step 2: Server fetches the latest status from the database.
@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    try:
        item = aws.get_job_item(job_id)
        if not item:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(
            JobId=item.get("JobId"),
            Status=item.get("Status"),
            OutputUrl=item.get("OutputUrl"),
            CreatedAt=aws.decimal_convert(item.get("CreatedAt", 0)),
            UpdatedAt=aws.decimal_convert(item.get("UpdatedAt", 0)),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 5.3b Endpoint: SSE Job Status Stream
# Server-Sent Events endpoint that pushes status updates to the client.
# Replaces client-side polling to reduce DynamoDB reads and bandwidth.
@app.get("/api/status/{job_id}/stream")
async def stream_job_status(job_id: str):
    async def event_generator():
        last_status = None
        while True:
            try:
                item = aws.get_job_item(job_id)
                if not item:
                    yield {
                        "event": "error",
                        "data": json.dumps({"detail": "Job not found"}),
                    }
                    return

                current_status = item.get("Status")
                data = {
                    "JobId": item.get("JobId"),
                    "Status": current_status,
                    "OutputUrl": item.get("OutputUrl"),
                    "CreatedAt": aws.decimal_convert(item.get("CreatedAt", 0)),
                    "UpdatedAt": aws.decimal_convert(item.get("UpdatedAt", 0)),
                    "LastError": item.get("LastError"),
                }

                # Only send event when status actually changes, or on first poll
                if current_status != last_status:
                    yield {
                        "event": "status",
                        "data": json.dumps(data),
                    }
                    last_status = current_status

                # Terminal states: close the stream
                if current_status in ("Done", "Failed"):
                    return

            except Exception as e:
                logger.error(f"SSE stream error for job {job_id}: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": str(e)}),
                }
                return

            # Server-side poll interval (2 seconds)
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


# 5.4 Endpoint: Instant Preview
# Step 1: User uploads a DOCX for immediate parsing and preview (synchronous).
# Step 2: Server reads file contents.
# Step 3: Server triggers the preview processing service (parsing questions, formulas, etc.).
# Step 4: Server returns the parsed exam data for the frontend to render.
@app.post("/api/preview", response_model=PreviewResponse)
async def preview_exam(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    try:
        contents = await file.read()
        # Synchronously process the file for preview.
        preview_data = await process_preview(contents)

        return PreviewResponse(status="success", data=preview_data)

    except ExamError as e:
        # Known application-specific errors.
        logger.warning(f"Preview Logic Error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        # Unexpected errors (corrupt files, etc.).
        logger.error(f"Preview Error: {str(e)}", exc_info=True)
        if "BadZipFile" in str(type(e).__name__):
            raise HTTPException(
                status_code=400,
                detail="DOCX file is corrupted (Bad Zip). Please try another file.",
            )
        if "PackageNotFoundError" in str(type(e).__name__):
            raise HTTPException(
                status_code=400, detail="File is not a valid DOCX format."
            )
        raise HTTPException(
            status_code=500, detail=f"System error while processing file: {str(e)}"
        )


# -- 6. Exception Handlers --
# Global handler for ExamError to return uniform error objects to the frontend.
@app.exception_handler(ExamError)
async def exam_error_handler(request, exc: ExamError):  # type: ignore
    return JSONResponse(
        status_code=400, content={"detail": exc.message, "code": exc.code}
    )


# -- 7. Server Entry Point --
# Starts the server using Uvicorn on port 5000.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
