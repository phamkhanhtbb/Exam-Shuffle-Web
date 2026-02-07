import base64
import re
from lxml import etree
from docx.document import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from core.image_processor import ImageProcessor
from core.math_processor import MathProcessor

# Namespace cho việc tìm kiếm XML
nsmap = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'
}



class DocxSerializer:
    def __init__(self, doc_obj, answer_map: dict = None):
        self.doc = doc_obj
        self.assets = {}
        self.img_count = 0
        self.math_count = 0
        self.answer_map = answer_map or {}
        self.current_q_num = 0
        
        # Initialize processors
        self.image_processor = ImageProcessor()
        self.math_processor = MathProcessor(nsmap)

        # --- CẤU HÌNH REGEX LOẠI TRỪ IN ĐẬM ---
        # 1. Label câu hỏi: "Câu 1", "Câu 1.", "Bài 1:", "Câu 10" (case insensitive)
        # 2. Label đáp án: "A.", "B)", "c.", "d:" (ký tự đơn + dấu chấm/ngoặc/hai chấm)
        self.ignore_bold_pattern = re.compile(
            r"^\s*(?:Câu|Bài|Phần)\s+\d+[\.:]*\s*$|"  # Matches: Câu 1, Câu 1., Bài 2:
            r"^\s*[A-Da-d][\.\\):]?\s*$",  # Matches: A., B), c:, d.
            re.IGNORECASE
        )
        # Regex to detect Question Number Update
        self.q_num_pattern = re.compile(r"^\s*(?:Câu|Bài)\s+(\d+)", re.IGNORECASE)
        # Regex to detect Option Start: A. B. ...
        self.opt_pattern = re.compile(r"^\s*([A-D])[\.\)]", re.IGNORECASE)

    def _get_image_data(self, blip_id):
        """Lấy binary data của ảnh từ rId"""
        try:
            part = self.doc.part.related_parts[blip_id]
            return part.blob
        except:
            return None

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
                        
                        # Use ImageProcessor to convert if needed (though usually drawing blips are standard)
                        # But standard drawing blips are usually PNG/JPEG/etc.
                        # We just encode them.
                        # Wait, original code was just b64encode for drawing images.
                        # Logic: "if img_bytes: ... b64encode(img_bytes)"
                        # Let's keep it simple or use ImageProcessor for consistency?
                        # Original code:
                        # b64_str = base64.b64encode(img_bytes).decode('utf-8')
                        # self.assets[img_id] = {"type": "image", "src": f"data:image/png;base64,{b64_str}"}
                        # Problem: if it's not PNG? 
                        # Let's use ImageProcessor to be safe and consistent
                        src = self.image_processor.convert_image_to_png(img_bytes, img_id)
                        
                        self.assets[img_id] = {
                            "type": "image",
                            "src": src
                        }
                        return f"[img:${img_id}$]"

        # 2. Xử lý MATH
        # Delegate to MathProcessor
        if "m:oMath" in xml_str or "w:object" in xml_str:
            self.math_count += 1
            math_id = f"mathtype_{self.math_count}"
            
            latex_str = self.math_processor.extract_latex_from_run(run._element)
            img_src = None
            
            # If no latex found or fallback needed, check for OLE Object Image
            if not latex_str:
                objects = run._element.findall('.//w:object', namespaces=nsmap)
                for obj in objects:
                     res = self.math_processor.extract_ole_image_bytes(obj, self._get_image_data)
                     if res:
                         img_bytes, rId = res
                         img_src = self.image_processor.convert_image_to_png(img_bytes, math_id)
                         if img_src:
                             print(f"[DEBUG] Extracted and converted image for {math_id}")
                         break
            
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
            
            # 1. Handle oMath/oMathPara (MathProcessor)
            if tag in ('oMathPara', 'oMath'):
                # For oMathPara, we need to find internal oMaths or treat the whole thing?
                # omml_to_latex handles oMathPara wrapping.
                # But here we stick to the pattern of one asset per math object
                
                # MathProcessor.process_omml_element handles the conversion
                latex_str = self.math_processor.process_omml_element(child)
                
                if latex_str:
                    self.math_count += 1
                    math_id = f"mathtype_{self.math_count}"
                    self.assets[math_id] = {
                        "type": "math",
                        "latex": latex_str,
                        "placeholder": "[Công thức]"
                    }
                    line_content += f"[!m:${math_id}$]"
            
            # 2. Handle runs (text, images, inline math)
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
        
        # --- LOGIC AUTO-MARKING ---
        clean_text = re.sub(r"\[![a-z]:|\]", "", line_content).strip()
        
        # 1. Update Current Question Number
        q_match = self.q_num_pattern.match(clean_text)
        if q_match:
            try:
                self.current_q_num = int(q_match.group(1))
            except:
                pass
        
        # 2. Check if this is an Option line for the current question
        if self.current_q_num and self.current_q_num in self.answer_map:
            correct_char = self.answer_map[self.current_q_num] # e.g. "A"
            
            opt_match = self.opt_pattern.match(clean_text)
            if opt_match:
                opt_char = opt_match.group(1).upper()
                if opt_char == correct_char.upper():
                    # MARK IT!
                    # Only mark if not already marked with *
                    if not line_content.strip().startswith("*"):
                        # Prepend * to line_content
                        # Be careful with leading spaces or tags
                        # Just naive prepend
                        line_content = "*" + line_content

        return line_content

    def _process_table(self, table) -> str:
        """Chuyển bảng thành format [* Col | Col *]"""
        lines = []
        for row in table.rows:
            cells_txt = []
            for cell in row.cells:
                # _process_paragraph đã bao gồm logic clean label & auto-mark
                cell_content = " ".join([self._process_paragraph(p) for p in cell.paragraphs])
                cells_txt.append(cell_content.strip())
            row_str = "[* " + " | ".join(cells_txt) + " *]"
            lines.append(row_str)
        return "\n".join(lines)

    def serialize(self) -> dict:
        """Hàm chính gọi từ bên ngoài"""
        raw_lines = []
        
        # Import regex constants
        from core.constants import END_NOTE_PATTERN, ANSWER_HEADER_PATTERN
        
        # Helper check for "Đáp án: ..." line (inline answer)
        # Note: ANSWER_HEADER_PATTERN matches global header, we need to detect "Đáp án: " content line.
        # Reuse logic or simple regex:
        inline_ans_pattern = re.compile(r"^(?:Đáp án|ĐÁP ÁN|Dap an)[:\.]", re.IGNORECASE)

        for child in self.doc.element.body.iterchildren():
            txt = ""
            if isinstance(child, CT_P):
                para = Paragraph(child, self.doc)
                txt = self._process_paragraph(para)
            elif isinstance(child, CT_Tbl):
                table = Table(child, self.doc)
                txt = self._process_table(table)
            
            if txt.strip():
                # Check for reordering: "HẾT" then "Đáp án: ..." -> Swap
                # Only check if we have lines
                if raw_lines:
                    last_line = raw_lines[-1]
                    
                    # Clean tags from last_line to check pattern
                    # Tags like [!b:...] or [!m:...]
                    clean_last = re.sub(r"\[![a-z]:|\]", "", last_line).strip()
                    
                    # Clean tags from current txt to check pattern
                    clean_txt = re.sub(r"\[![a-z]:|\]", "", txt).strip()

                    # Robust check for HẾT (case insensitive, contains HẾT)
                    # Use strictly END_NOTE_PATTERN logic but on clean text? 
                    # Or just: "HẾT" surrounded by dashes or similar?
                    # Let's stick to END_NOTE_PATTERN but ensure it covers unicode dashes if needed,
                    # OR just check for HẾT word boundary?
                    # User's HẾT is usually "------ HẾT ------"
                    
                    is_end_marker = False
                    if "HẾT" in clean_last.upper():
                         is_end_marker = True
                    
                    if is_end_marker:
                        # Check if current line is "Đáp án: ..."
                        if inline_ans_pattern.match(clean_txt):
                             print(f"DEBUG: Swapping '{clean_txt}' with '{clean_last}'")
                             # Insert BEFORE the last line
                             raw_lines.insert(-1, txt)
                             continue
                
                raw_lines.append(txt)

        return {
            "raw_text": "\n".join(raw_lines),
            "assets_map": self.assets
        }