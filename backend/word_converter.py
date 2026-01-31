"""
MS Word Automation Converter Module
Uses win32com to control Microsoft Word for converting MathType to native OMML.
"""
import os
import tempfile
import pythoncom
import win32com.client
import shutil
from pathlib import Path

def convert_with_word_automation(input_bytes: bytes) -> bytes:
    """
    Convert a DOCX file using MS Word Automation to normalize MathType equations.
    
    Args:
        input_bytes: Raw bytes of the input DOCX file
        
    Returns:
        Raw bytes of the converted DOCX file
        
    Raises:
        RuntimeError: If conversion fails
    """
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="word_convert_")
    
    # Initialize COM for this thread (crucial for FastAPI)
    pythoncom.CoInitialize()
    
    word = None
    doc = None
    
    try:
        # Write input file
        input_path = os.path.join(temp_dir, "input.docx")
        # Use full absolute path for Word
        input_path = os.path.abspath(input_path)
        
        with open(input_path, "wb") as f:
            f.write(input_bytes)
            
        print(f"[Word] Starting Word application...")
        
        try:
            # Try to get existing instance or create new one
            word = win32com.client.Dispatch("Word.Application")
        except Exception:
            word = win32com.client.DispatchEx("Word.Application")
            
        # Make it invisible but usually faster to process
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone
        
        print(f"[Word] Opening document: {input_path}")
        doc = word.Documents.Open(input_path)
        
        # Aggressive conversion: Round-trip to RTF
        # This forces Word to rewrite OLE objects
        rtf_path = os.path.join(temp_dir, "temp.rtf")
        rtf_path = os.path.abspath(rtf_path)
        
        print(f"[Word] Round-tripping via RTF to force conversion...")
        
        # FileFormat=6 is wdFormatRTF
        doc.SaveAs2(rtf_path, FileFormat=6)
        doc.Close()
        doc = None
        
        # Re-open RTF
        doc = word.Documents.Open(rtf_path)
        
        # Save back to DOCX
        # FileFormat=16 is wdFormatDocumentDefault (DOCX)
        print(f"[Word] Saving back to DOCX...")
        doc.SaveAs2(input_path, FileFormat=16)
        doc.Close()
        doc = None
        
        # Read back the file
        with open(input_path, "rb") as f:
            return f.read()
            
    except Exception as e:
        print(f"[Word] Error during conversion: {e}")
        raise RuntimeError(f"Word automation failed: {e}")
        
    finally:
        # Cleanup Word resources
        if doc:
            try:
                doc.Close(SaveChanges=0) # wdDoNotSaveChanges
            except:
                pass
                
        # We don't Quit() Word because it might be used by user, 
        # but if we created a specific instance (DispatchEx) maybe we should.
        # For safety/speed, let's keep it running or let user manage it, 
        # or we could try to be polite. 
        # Given this is a local tool, maybe quitting is safer if we started it?
        # Let's just release COM object.
        word = None
        
        # Uninitialize COM
        pythoncom.CoUninitialize()
        
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"[Word] Failed to cleanup temp dir: {e}")

def is_word_available() -> bool:
    """Check if MS Word is available via COM"""
    try:
        pythoncom.CoInitialize()
        try:
            win32com.client.Dispatch("Word.Application")
            return True
        except:
            return False
        finally:
            pythoncom.CoUninitialize()
    except:
        return False

if __name__ == "__main__":
    print(f"Word available: {is_word_available()}")
