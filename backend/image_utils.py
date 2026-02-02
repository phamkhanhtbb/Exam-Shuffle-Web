import base64
import io
import tempfile
import os
import ctypes
from typing import Optional

def convert_image_to_png(img_bytes: bytes, math_id: str) -> Optional[str]:
    """Convert WMF/EMF/Other images to PNG for browser compatibility"""
    # Check magic bytes to detect format
    if img_bytes[:4] == b'\xd7\xcd\xc6\x9a':
        # WMF Placeable Header
        print(f"[DEBUG] {math_id}: Detected WMF format")
        return _try_convert_wmf_emf(img_bytes, 'wmf', math_id)
    elif img_bytes[:4] == b'\x01\x00\x00\x00':
        # EMF header
        print(f"[DEBUG] {math_id}: Detected EMF format")
        return _try_convert_wmf_emf(img_bytes, 'emf', math_id)
    elif img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        # Already PNG
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/png;base64,{b64_str}"
    elif img_bytes[:2] == b'\xff\xd8':
        # JPEG
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{b64_str}"
    elif img_bytes[:6] in (b'GIF87a', b'GIF89a'):
        # GIF
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/gif;base64,{b64_str}"
    else:
        # Unknown format, try to convert anyway
        print(f"[DEBUG] {math_id}: Unknown format, attempting conversion")
        return _try_convert_wmf_emf(img_bytes, 'unknown', math_id)

def _try_convert_wmf_emf(img_bytes: bytes, fmt: str, math_id: str) -> str:
    """Try to convert WMF/EMF using pywin32 (Windows GDI) or Pillow"""
    
    # Try pywin32 for WMF/EMF on Windows
    if fmt in ('wmf', 'emf'):
        try:
            import win32ui
            import win32gui
            from PIL import Image
            
            # Check for Placeable WMF header (APM) and strip it
            # Magic number: 0x9AC6CDD7
            if fmt == 'wmf' and img_bytes[:4] == b'\xd7\xcd\xc6\x9a':
                print(f"[DEBUG] {math_id}: Stripping 22-byte WMF header")
                data_bytes = img_bytes[22:]
            else:
                data_bytes = img_bytes

            hmf = None
            
            try:
                # Method 1: Load directly from bytes using GDI via ctypes
                if fmt == 'wmf':
                    # SetWinMetaFileBits returns a handle to a memory-based enhanced metafile
                    hmf = ctypes.windll.gdi32.SetWinMetaFileBits(
                        len(data_bytes), 
                        data_bytes, 
                        None, 
                        None
                    )
                else:
                    # SetEnhMetaFileBits
                    hmf = ctypes.windll.gdi32.SetEnhMetaFileBits(
                        len(data_bytes), 
                        data_bytes
                    )
            except Exception as load_err:
                print(f"[DEBUG] {math_id}: GDI loading failed: {load_err}, trying temp file")
            
            # Method 2: Fallback to Temp File (Standard loading)
            if not hmf or hmf == 0:
                with tempfile.NamedTemporaryFile(suffix=f'.{fmt}', delete=False) as tmp:
                    tmp.write(data_bytes) # Write raw data (stripped if WMF)
                    tmp_path = tmp.name
                try:
                    # Try loading with GDI
                    hmf = ctypes.windll.gdi32.GetEnhMetaFileW(tmp_path)
                except Exception as e:
                        print(f"[DEBUG] {math_id}: Temp file load failed: {e}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

            if not hmf or hmf == 0:
                raise RuntimeError("Could not create Metafile handle")

            # Use Windows GDI to render
            # Create a device context
            dc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            memdc = dc.CreateCompatibleDC()
            
            # Get metafile header for size using ctypes
            class ENHMETAHEADER(ctypes.Structure):
                _fields_ = [
                    ("iType", ctypes.c_int),
                    ("nSize", ctypes.c_int),
                    ("rclBounds", ctypes.c_long * 4),
                    ("rclFrame", ctypes.c_long * 4),
                    ("dSignature", ctypes.c_int),
                    ("nVersion", ctypes.c_int),
                    ("nBytes", ctypes.c_int),
                    ("nRecords", ctypes.c_int),
                    ("nHandles", ctypes.c_ushort),
                    ("sReserved", ctypes.c_ushort),
                    ("nDescription", ctypes.c_int),
                    ("offDescription", ctypes.c_int),
                    ("nPalEntries", ctypes.c_int),
                    ("rclDevice", ctypes.c_long * 4),
                    ("szlDevice", ctypes.c_int * 2),
                ]
            
            header = ENHMETAHEADER()
            res = ctypes.windll.gdi32.GetEnhMetaFileHeader(hmf, ctypes.sizeof(header), ctypes.byref(header))
            
            if res == 0:
                    width = 200
                    height = 100
            else:
                # rclFrame is in 0.01mm units
                width_mm = (header.rclFrame[2] - header.rclFrame[0]) / 100.0
                height_mm = (header.rclFrame[3] - header.rclFrame[1]) / 100.0
                
                # High resolution render (Scale 3.0 for Retina-like sharpness)
                scale = 3.0 
                width = int(width_mm * 96 / 25.4 * scale)
                height = int(height_mm * 96 / 25.4 * scale)
            
            width = max(width, 50)
            height = max(height, 20)

            # Create bitmap
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(dc, width, height)
            memdc.SelectObject(bmp)
            
            # Fill with white background
            memdc.FillSolidRect((0, 0, width, height), 0xFFFFFF)
            
            # Play the metafile onto the DC
            win32gui.PlayEnhMetaFile(memdc.GetSafeHdc(), hmf, (0, 0, width, height))
            
            # Get bitmap bits
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)
            
            # Convert to PIL Image
            img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
                                    bmpstr, 'raw', 'BGRX', 0, 1)
            
            # Save as PNG
            png_io = io.BytesIO()
            img.save(png_io, format='PNG')
            png_bytes = png_io.getvalue()
            
            # Cleanup handle
            ctypes.windll.gdi32.DeleteEnhMetaFile(hmf)
            memdc.DeleteDC()
            
            b64_str = base64.b64encode(png_bytes).decode('utf-8')
            print(f"[DEBUG] {math_id}: Successfully converted {fmt} to PNG using pywin32 (High Quality)")
            return f"data:image/png;base64,{b64_str}"
                
        except Exception as e:
            print(f"[DEBUG] {math_id}: pywin32 conversion failed ({fmt}): {e}")
    
    # Fallback to Pillow for other formats
    try:
        from PIL import Image
        img_io = io.BytesIO(img_bytes)
        img = Image.open(img_io)
        png_io = io.BytesIO()
        img.convert('RGBA').save(png_io, format='PNG')
        png_bytes = png_io.getvalue()
        b64_str = base64.b64encode(png_bytes).decode('utf-8')
        print(f"[DEBUG] {math_id}: Successfully converted {fmt} to PNG using Pillow")
        return f"data:image/png;base64,{b64_str}"
    except Exception as e:
        print(f"[DEBUG] {math_id}: Pillow conversion also failed ({fmt}): {e}")
        
    # Final fallback: return raw bytes
    b64_str = base64.b64encode(img_bytes).decode('utf-8')
    if fmt == 'wmf':
        return f"data:image/x-wmf;base64,{b64_str}"
    elif fmt == 'emf':
        return f"data:image/x-emf;base64,{b64_str}"
    else:
        return f"data:application/octet-stream;base64,{b64_str}"
