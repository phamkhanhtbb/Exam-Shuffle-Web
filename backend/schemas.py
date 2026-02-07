from typing import List, Optional, Dict
from pydantic import BaseModel


# --- REQUEST MODELS ---

class UploadUrlRequest(BaseModel):
    fileName: str
    fileType: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class SubmitJobRequest(BaseModel):
    jobId: str
    fileKey: str
    numVariants: int = 10
    rawText: Optional[str] = None


# --- RESPONSE MODELS ---

class UploadUrlResponse(BaseModel):
    jobId: str
    uploadUrl: str
    fileKey: str


class SubmitJobResponse(BaseModel):
    message: str
    jobId: str


class JobStatusResponse(BaseModel):
    JobId: str
    Status: str
    OutputUrl: Optional[str] = None
    CreatedAt: int
    UpdatedAt: int


class PreviewData(BaseModel):
    raw_text: str
    assets_map: Dict[str, Dict]
    question_count: int = 0


class PreviewResponse(BaseModel):
    status: str
    data: PreviewData


class ErrorResponse(BaseModel):
    error: str
