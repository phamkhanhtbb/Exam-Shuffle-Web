import base64
import re
from lxml import etree
from docx.document import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.shape import CT_BlipFillProperties
from omml_to_latex import omml_to_latex

# Namespace cho việc tìm kiếm XML
nsmap = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'
}


class DocxSerializer:
    def __init__(self, doc_obj):
        self.doc = doc_obj
        self.assets = {}
        self.img_count = 0
        self.math_count = 0

        # --- CẤU HÌNH REGEX LOẠI TRỪ IN ĐẬM ---
        # 1. Label câu hỏi: "Câu 1", "Câu 1.", "Bài 1:", "Câu 10" (case insensitive)
        # 2. Label đáp án: "A.", "B)", "c.", "d:" (ký tự đơn + dấu chấm/ngoặc/hai chấm)
        self.ignore_bold_pattern = re.compile(
            r"^\s*(?:Câu|Bài|Phần)\s+\d+[\.:]*\s*$|"  # Matches: Câu 1, Câu 1., Bài 2:
            r"^\s*[A-Da-d][\.\\):]?\s*$",  # Matches: A., B), c:, d.
            re.IGNORECASE
        )

    def _get_image_data(self, blip_id):
        """Lấy binary data của ảnh từ rId"""
        try:
            part = self.doc.part.related_parts[blip_id]
            return part.blob
        except:
            return None

    def _convert_image_to_png(self, img_bytes, math_id):
        """Convert WMF/EMF to PNG for browser compatibility"""
        import io
        
        # Check magic bytes to detect format
        if img_bytes[:4] == b'\xd7\xcd\xc6\x9a':
            # WMF Placeable Header
            print(f"[DEBUG] {math_id}: Detected WMF format")
            return self._try_convert_wmf_emf(img_bytes, 'wmf', math_id)
        elif img_bytes[:4] == b'\x01\x00\x00\x00':
            # EMF header
            print(f"[DEBUG] {math_id}: Detected EMF format")
            return self._try_convert_wmf_emf(img_bytes, 'emf', math_id)
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
            return self._try_convert_wmf_emf(img_bytes, 'unknown', math_id)

    def _try_convert_wmf_emf(self, img_bytes, fmt, math_id):
        """Try to convert WMF/EMF using pywin32 (Windows GDI) or Pillow"""
        import io
        import tempfile
        import os
        import ctypes
        
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
                        # UINT SetWinMetaFileBits(UINT cbBuffer, const BYTE *lpbBuffer, HDC hdcRef, const METAFILEPICT *lpmfp);
                        # We pass None for hdcRef and lpmfp to use defaults
                        hmf = ctypes.windll.gdi32.SetWinMetaFileBits(
                            len(data_bytes), 
                            data_bytes, 
                            None, 
                            None
                        )
                    else:
                        # SetEnhMetaFileBits
                        # HENHMETAFILE SetEnhMetaFileBits(UINT cbBuffer, const BYTE *pbBuffer);
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

    def _is_label(self, text):
        """Kiểm tra xem text có phải là label (Câu hỏi/Đáp án) cần bỏ in đậm không"""
        if not text: return False
        # Xóa khoảng trắng thừa để check regex chính xác hơn
        return bool(self.ignore_bold_pattern.match(text.strip()))

    def _process_run(self, run, paragraph) -> str:
        """Xử lý từng Run: Check BOLD, IMAGE, MATH"""
        text = run.text
        xml_str = run._element.xml

        # 1. Xử lý ẢNH (Drawing)
        drawings = run._element.findall('.//w:drawing', namespaces=nsmap)
        for drawing in drawings:
            blips = drawing.findall('.//a:blip', namespaces=nsmap)
            for blip in blips:
                rId = blip.get(f"{{{nsmap['r']}}}embed")
                if rId:
                    img_bytes = self._get_image_data(rId)
                    if img_bytes:
                        self.img_count += 1
                        img_id = f"img_{self.img_count}"
                        b64_str = base64.b64encode(img_bytes).decode('utf-8')
                        self.assets[img_id] = {
                            "type": "image",
                            "src": f"data:image/png;base64,{b64_str}"
                        }
                        return f"[img:${img_id}$]"

        # 2. Xử lý MATH
        if "m:oMath" in xml_str or "w:object" in xml_str:
            self.math_count += 1
            math_id = f"mathtype_{self.math_count}"
            
            # Extract and convert OMML to LaTeX
            latex_str = None
            img_src = None
            
            try:
                # Try to find oMath elements first (direct OMML math)
                omath_elements = run._element.findall('.//m:oMath', namespaces=nsmap)
                
                # If not found, try oMathPara (paragraph-level math container)
                if not omath_elements:
                    omath_para = run._element.findall('.//m:oMathPara', namespaces=nsmap)
                    if omath_para:
                        omath_elements = omath_para[0].findall('.//m:oMath', namespaces=nsmap)
                
                if omath_elements:
                    omml_xml = etree.tostring(omath_elements[0], encoding='unicode')
                    latex_str = omml_to_latex(omml_xml)
                else:
                    # Handle MathType OLE objects (w:object)
                    # Try to find OMML in mc:AlternateContent (Word sometimes provides OMML fallback)
                    alt_content_ns = {'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006'}
                    alt_omath = run._element.findall('.//mc:Choice//m:oMath', namespaces={**nsmap, **alt_content_ns})
                    if alt_omath:
                        omml_xml = etree.tostring(alt_omath[0], encoding='unicode')
                        latex_str = omml_to_latex(omml_xml)
                    else:
                        # For pure MathType OLE, try to extract the embedded WMF/EMF image
                        objects = run._element.findall('.//w:object', namespaces=nsmap)
                        for obj in objects:
                            # Look for embedded picture (imagedata with r:id)
                            shape_ns = {'v': 'urn:schemas-microsoft-com:vml'}
                            imagedata = obj.findall('.//v:imagedata', namespaces=shape_ns)
                            for img in imagedata:
                                rId = img.get(f"{{{nsmap['r']}}}id")
                                if rId:
                                    img_bytes = self._get_image_data(rId)
                                    if img_bytes:
                                        # Try to convert image to PNG for browser compatibility
                                        img_src = self._convert_image_to_png(img_bytes, math_id)
                                        if img_src:
                                            print(f"[DEBUG] Extracted and converted image for {math_id}")
                                        break
                            if img_src:
                                break
                                
            except Exception as e:
                print(f"LaTeX/Image extraction failed for {math_id}: {e}")
            
            # Store asset with latex or image fallback
            self.assets[math_id] = {
                "type": "math",
                "latex": latex_str,
                "src": img_src,  # Fallback image for MathType
                "placeholder": "[Công thức]"
            }
            return f"[!m:${math_id}$]"

        # 4. Xử lý BOLD
        # Chỉ đánh dấu, việc check label sẽ làm ở bước _process_paragraph (gộp string)
        if run.bold and text.strip():
            return f"[!b:{text}]"

        return text

    def _clean_bold_labels(self, text):
        """
        Hậu xử lý: Tìm các chuỗi [!b:...] liên tiếp.
        Nếu nội dung gộp của chúng khớp pattern label -> Xóa tag [!b:]
        Ví dụ: "[!b:Câu][!b: 1.]" -> "Câu 1."
        """
        # Pattern: Tìm chuỗi các tag [!b:...] đứng cạnh nhau (có thể có space ở giữa các tag)
        # Group 1: Toàn bộ chuỗi match
        pattern = re.compile(r"((?:\[!b:[^\]]+\]\s*)+)")

        def replacer(match):
            full_str = match.group(1)
            # Lấy nội dung thô bằng cách xóa tag [!b: và ]
            # (Giả định trong text không có chuỗi '[!b:' hoặc ']' trùng lặp gây lỗi - an toàn với text Word thường)
            raw_text = re.sub(r"\[!b:|\]", "", full_str)

            # Kiểm tra text thô có phải label không
            if self._is_label(raw_text):
                return raw_text  # Trả về text gốc (đã bỏ in đậm)
            else:
                return full_str  # Giữ nguyên format in đậm

        return pattern.sub(replacer, text)

    def _process_inline_latex_text(self, text):
        """
        Process inline LaTeX ($...$) in full paragraph text.
        Handles masking of existing [!m:...] tags.
        """
        if '$' not in text:
            return text
            
        import re
        # 1. Mask existing math assets
        existing_tags = []
        def mask_tag(match):
            tag = match.group(0)
            existing_tags.append(tag)
            return f"__MATH_TAG_{len(existing_tags)-1}__"
            
        try:
            # Mask [!m:...] AND [img:...] tags to protect them from regex replacement
            # Image tags format: [img:$id$]
            # Math tags format: [!m:$id$]
            temp_text = re.sub(r'(\[!m:[^\]]+\$\]|\[img:\$[^\]]+\$\])', mask_tag, text)
            
            # 2. Process inline latex $...$
            def replace_latex(match):
                latex_content = match.group(1)
                # Avoid empty matches or whitespace only if undesired
                if not latex_content.strip():
                    return match.group(0)
                
                self.math_count += 1
                math_id = f"mathtype_{self.math_count}"
                
                self.assets[math_id] = {
                    "type": "math",
                    "latex": latex_content,
                    "src": None,
                    "placeholder": "[Công thức]"
                }
                return f"[!m:${math_id}$]"

            # Regex: $...$
            # Support escaped \$? For now basic non-greedy
            temp_text = re.sub(r'\$([^\$]+)\$', replace_latex, temp_text)
            
            # 3. Restore masked tags
            for i, tag in enumerate(existing_tags):
                temp_text = temp_text.replace(f"__MATH_TAG_{i}__", tag)
                
            return temp_text
            
        except Exception as e:
            print(f"Inline latex processing error: {e}")
            return text

    def _process_paragraph(self, paragraph) -> str:
        """Ghép các Run lại thành dòng và làm sạch label"""
        line_content = ""
        
        # First, check for paragraph-level m:oMath or m:oMathPara elements
        # These are direct children of the paragraph, not inside runs
        para_xml = paragraph._element
        
        # Process all children of paragraph element in order
        for child in para_xml:
            tag = etree.QName(child.tag).localname if child.tag else ''
            
            # Handle oMathPara (math paragraph container)
            if tag == 'oMathPara':
                omath_elements = child.findall('.//m:oMath', namespaces=nsmap)
                for omath in omath_elements:
                    self.math_count += 1
                    math_id = f"mathtype_{self.math_count}"
                    latex_str = None
                    try:
                        omml_xml = etree.tostring(omath, encoding='unicode')
                        latex_str = omml_to_latex(omml_xml)
                    except Exception as e:
                        print(f"LaTeX conversion failed for {math_id}: {e}")
                    
                    self.assets[math_id] = {
                        "type": "math",
                        "latex": latex_str,
                        "placeholder": "[Công thức]"
                    }
                    line_content += f"[!m:${math_id}$]"
            
            # Handle standalone oMath (direct child of paragraph)
            elif tag == 'oMath':
                self.math_count += 1
                math_id = f"mathtype_{self.math_count}"
                latex_str = None
                try:
                    omml_xml = etree.tostring(child, encoding='unicode')
                    latex_str = omml_to_latex(omml_xml)
                except Exception as e:
                    print(f"LaTeX conversion failed for {math_id}: {e}")
                
                self.assets[math_id] = {
                    "type": "math",
                    "latex": latex_str,
                    "placeholder": "[Công thức]"
                }
                line_content += f"[!m:${math_id}$]"
            
            # Handle runs (text, images, inline math)
            elif tag == 'r':
                # Find the corresponding run in paragraph.runs by matching XML element
                for run in paragraph.runs:
                    if run._element is child:
                        line_content += self._process_run(run, paragraph)
                        break

        # Check for inline LaTeX text ($...$) in the full combined line
        line_content = self._process_inline_latex_text(line_content)

        # BƯỚC QUAN TRỌNG: Làm sạch label bị split
        line_content = self._clean_bold_labels(line_content)

        return line_content

    def _process_table(self, table) -> str:
        """Chuyển bảng thành format [* Col | Col *]"""
        lines = []
        for row in table.rows:
            cells_txt = []
            for cell in row.cells:
                # _process_paragraph đã bao gồm logic clean label
                cell_content = " ".join([self._process_paragraph(p) for p in cell.paragraphs])
                cells_txt.append(cell_content.strip())
            row_str = "[* " + " | ".join(cells_txt) + " *]"
            lines.append(row_str)
        return "\n".join(lines)

    def serialize(self) -> dict:
        """Hàm chính gọi từ bên ngoài"""
        raw_lines = []
        for child in self.doc.element.body.iterchildren():
            if isinstance(child, CT_P):
                para = Paragraph(child, self.doc)
                txt = self._process_paragraph(para)
                if txt.strip(): raw_lines.append(txt)
            elif isinstance(child, CT_Tbl):
                table = Table(child, self.doc)
                txt = self._process_table(table)
                raw_lines.append(txt)

        return {
            "raw_text": "\n".join(raw_lines),
            "assets_map": self.assets
        }