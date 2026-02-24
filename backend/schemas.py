"""
Data Schemas for API Requests and Responses.

This module defines Pydantic models used for data validation and 
serialization across the FastAPI endpoints.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel

# --- REQUEST MODELS ---
# These models define the expected structure of data sent BY the client.

class UploadUrlRequest(BaseModel):
    """Initial request to get an S3 upload URL for a DOCX file."""
    fileName: str
    fileType: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

class SubmitJobRequest(BaseModel):
    """Request to start a background processing job for a specific file."""
    jobId: str
    fileKey: str
    numVariants: int = 10
    rawText: Optional[str] = None      # Optional raw text content from the editor.
    examCodes: Optional[str] = None    # User-defined exam codes (e.g., "101, 102").

# --- RESPONSE MODELS ---
# These models define the structure of data returned TO the client.

class UploadUrlResponse(BaseModel):
    """Successful response providing a temporary S3 upload location."""
    jobId: str
    uploadUrl: str
    fileKey: str

class SubmitJobResponse(BaseModel):
    """Confirmation that a job has been successfully queued."""
    message: str
    jobId: str

class JobStatusResponse(BaseModel):
    """Detailed status update for a specific processing job."""
    JobId: str
    Status: str
    OutputUrl: Optional[str] = None   # Presigned URL to the resulting ZIP.
    CreatedAt: int
    UpdatedAt: int

# --- PREVIEW MODELS ---
# Models for the 'Preview' feature which parses a DOCX for display in the browser.

class PreviewData(BaseModel):
    """Structured content of a parsed DOCX template."""
    raw_text: str
    assets_map: Dict[str, Dict]       # Map of image/math asset IDs to their metadata.
    question_count: int = 0

class PreviewResponse(BaseModel):
    """Wrapper response for the preview data."""
    status: str
    data: PreviewData

class ErrorResponse(BaseModel):
    """Standardized error message format."""
    error: str
