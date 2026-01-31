"""
LibreOffice Converter Module
Converts DOCX files with MathType OLE objects to native OMML format
"""
import subprocess
import tempfile
import shutil
import os
from pathlib import Path

# LibreOffice executable path (Windows)
LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

def convert_with_libreoffice(input_bytes: bytes) -> bytes:
    """
    Convert a DOCX file using LibreOffice to normalize MathType equations.
    
    Args:
        input_bytes: Raw bytes of the input DOCX file
        
    Returns:
        Raw bytes of the converted DOCX file
        
    Raises:
        RuntimeError: If conversion fails
    """
    # Create temp directory for conversion
    temp_dir = tempfile.mkdtemp(prefix="lo_convert_")
    
    try:
        # Write input file
        input_path = os.path.join(temp_dir, "input.docx")
        with open(input_path, "wb") as f:
            f.write(input_bytes)
        
        # Step 1: Convert DOCX -> ODT (OpenDocument Text)
        # This acts as a sanitizer/converter for MathType
        print(f"[LibreOffice] Step 1: Converting DOCX -> ODT...")
        cmd_odt = [
            LIBREOFFICE_PATH,
            "--headless",
            "--invisible",
            "--convert-to", "odt",
            "--outdir", temp_dir,
            input_path
        ]
        
        result_odt = subprocess.run(
            cmd_odt,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result_odt.returncode != 0:
            print(f"[LibreOffice] Step 1 failed: {result_odt.stderr}")
            raise RuntimeError(f"LibreOffice DOCX->ODT failed: {result_odt.stderr}")
            
        # Step 2: Convert ODT -> DOCX
        print(f"[LibreOffice] Step 2: Converting ODT -> DOCX...")
        odt_path = os.path.join(temp_dir, "input.odt")
        if not os.path.exists(odt_path):
             raise RuntimeError("Intermediate ODT file not found")

        cmd_docx = [
            LIBREOFFICE_PATH,
            "--headless",
            "--invisible",
            "--convert-to", "docx",
            "--outdir", temp_dir,
            odt_path
        ]
        
        result_docx = subprocess.run(
            cmd_docx,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result_docx.returncode != 0:
            print(f"[LibreOffice] Step 2 failed: {result_docx.stderr}")
            raise RuntimeError(f"LibreOffice ODT->DOCX failed: {result_docx.stderr}")
        
        print(f"[LibreOffice] Double conversion successful")
        
        # Read the converted file
        output_path = os.path.join(temp_dir, "input.docx")
        if not os.path.exists(output_path):
            # Sometimes output has different name
            docx_files = list(Path(temp_dir).glob("*.docx"))
            if docx_files:
                output_path = str(docx_files[0])
            else:
                raise RuntimeError("Converted file not found")
        
        with open(output_path, "rb") as f:
            return f.read()
            
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"[LibreOffice] Failed to cleanup temp dir: {e}")


def is_libreoffice_available() -> bool:
    """Check if LibreOffice is installed and accessible"""
    return os.path.exists(LIBREOFFICE_PATH)


if __name__ == "__main__":
    # Test
    print(f"LibreOffice available: {is_libreoffice_available()}")
    print(f"Path: {LIBREOFFICE_PATH}")
