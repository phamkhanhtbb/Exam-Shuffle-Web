import base64
import re
from docx.document import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.shape import CT_BlipFillProperties

# Namespace cho việc tìm kiếm XML (quan trọng để tìm ảnh/math)
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
        self.assets = {}  # Chứa data ảnh/math: {'img_1': 'base64...', 'math_2': 'xml...'}
        self.img_count = 0
        self.math_count = 0

    def _get_image_data(self, blip_id):
        """Lấy binary data của ảnh từ rId"""
        try:
            part = self.doc.part.related_parts[blip_id]
            return part.blob
        except:
            return None

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
                        # Lưu base64 để frontend hiển thị
                        b64_str = base64.b64encode(img_bytes).decode('utf-8')
                        self.assets[img_id] = {
                            "type": "image",
                            "src": f"data:image/png;base64,{b64_str}"
                        }
                        return f"[img:${img_id}$]"

        # 2. Xử lý MATH (Native OMML hoặc OLE MathType)
        # Note: MathType thường nằm trong w:object, Native Math nằm trong m:oMath
        # Đây là logic đơn giản hóa, thực tế MathType cần xử lý OLE Object
        if "m:oMath" in xml_str or "w:object" in xml_str:
            self.math_count += 1
            math_id = f"mathtype_{self.math_count}"
            # Với MathType, Word thường lưu 1 ảnh đại diện (fallback image)
            # Ta sẽ cố gắng lấy ảnh đó để hiển thị preview
            # (Logic lấy ảnh từ OLE object khá phức tạp, ở đây giả lập placeholder)
            self.assets[math_id] = {
                "type": "math",
                "latex": text,  # Nếu may mắn text chứa LaTeX
                "placeholder": "[Công thức]"
            }
            return f"[!m:${math_id}$]"

        # 3. Xử lý BOLD
        # Nếu run là bold và có text
        if run.bold and text.strip():
            return f"[!b:{text}]"

        return text

    def _process_paragraph(self, paragraph) -> str:
        """Ghép các Run lại thành dòng"""
        line_content = ""
        for run in paragraph.runs:
            line_content += self._process_run(run, paragraph)
        return line_content

    def _process_table(self, table) -> str:
        """Chuyển bảng thành format [* Col | Col *]"""
        lines = []
        for row in table.rows:
            cells_txt = []
            for cell in row.cells:
                # Đệ quy: Cell có thể chứa paragraph in đậm hoặc công thức
                cell_content = " ".join([self._process_paragraph(p) for p in cell.paragraphs])
                cells_txt.append(cell_content.strip())

            # Ghép thành format: [* Col 1 | Col 2 | Col 3 *]
            row_str = "[* " + " | ".join(cells_txt) + " *]"
            lines.append(row_str)
        return "\n".join(lines)

    def serialize(self) -> dict:
        """Hàm chính gọi từ bên ngoài"""
        raw_lines = []

        # Duyệt tuần tự qua các block (Paragraph hoặc Table)
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