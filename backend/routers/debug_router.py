
import os
import hashlib
import logging
import pkg_resources
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from omml_to_latex import omml_to_latex

# Setup logging
logger = logging.getLogger("debug_router")

router = APIRouter(prefix="/api/debug", tags=["Debug"])

def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return "Not Found"
    except Exception as e:
        return f"Error: {e}"

class OmmlRequest(BaseModel):
    xml: str

class OmmlResponse(BaseModel):
    latex: str | None
    error: str | None = None

@router.get("/version")
async def get_version_info():
    """Return file hashes of critical files to verify deployment version."""
    files_to_check = [
        "omml_to_latex.py",
        "core/math_processor.py",
        "services/docx_serializer.py",
        "server.py"
    ]
    
    hashes = {}
    base_dir = os.getcwd() # Should be /app or project root
    # Adjust if running from backend subdir or root
    # server.py is usually in backend/ or root. 
    # Based on previous context, server.py is in backend/server.py but we might be running from root project dir.
    # Let's check relative to this file? No, assume CWD is correct or try to find them.
    
    # Try current directory first
    for filename in files_to_check:
        # Check in current dir
        path = filename
        if not os.path.exists(path):
            # Try prepending backend/ if we are in project root
            path = os.path.join("backend", filename)
            
        hashes[filename] = get_file_hash(path)

    return {
        "files": hashes,
        "cwd": os.getcwd()
    }

@router.get("/env")
async def get_env_info():
    """Return installed packages and versions."""
    installed_packages = {d.project_name: d.version for d in pkg_resources.working_set}
    return {
        "packages": installed_packages,
        "python_version": os.sys.version
    }

@router.post("/convert-omml", response_model=OmmlResponse)
async def convert_omml(request: OmmlRequest):
    """Test OMML conversion directly."""
    try:
        logger.info(f"Debug conversion request (len={len(request.xml)})")
        latex = omml_to_latex(request.xml)
        return OmmlResponse(latex=latex)
    except Exception as e:
        logger.error(f"Debug conversion failed: {e}")
        return OmmlResponse(latex=None, error=str(e))
