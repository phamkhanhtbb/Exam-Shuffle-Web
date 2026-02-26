"""
DOCX Serializer — Converts a Word Document into a Structured Text/Asset Format.
This class iterates through the elements of a DOCX (paragraphs, tables) and
converts them into a plain-text representation while preserving important
components like Images, Math Formulas (LaTeX), and Bold text.
It also performs "Auto-Marking" of correct answers if an answer key is provided.
"""

import re
from lxml import etree
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from core.image_processor import ImageProcessor
from core.math_processor import MathProcessor

# --- XML Namespaces ---
# Used for searching specific elements (like math or images) inside the DOCX XML structure.
nsmap = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}


class DocxSerializer:
    def __init__(self, doc_obj, answer_map: dict = None):
        """
        Initializes the serializer with a python-docx object and an optional answer key.
        """
        self.doc = doc_obj
        self.assets = {}  # Stores extracted images and math formulas.
        self.img_count = 0
        self.math_count = 0
        self.answer_map = answer_map or {}
        self.current_q_num = 0
        self.global_q_counter = (
            0  # Global tracker to match answers across different parts.
        )

        # Helper processors for specialized tasks.
        self.image_processor = ImageProcessor()
        self.math_processor = MathProcessor(nsmap)

        # -- Regex Configuration --
        # 1. Labels: Detects identifiers like "Câu 1", "Bài 1", etc.
        # 2. Options: Detects labels like "A.", "B.", etc.
        self.ignore_bold_pattern = re.compile(
            r"^\s*(?:Câu|Bài|Phần)\s+\d+[\.:]*\s*$|"
            r"^\s*[A-Da-d][\.\\):]?\s*$",
            re.IGNORECASE,
        )
        self.q_num_pattern = re.compile(r"^\s*(?:Câu|Bài)\s+(\d+)", re.IGNORECASE)
        self.opt_pattern = re.compile(r"^\s*([A-D])[\.\)]", re.IGNORECASE)
        self.bold_chain_pattern = re.compile(r"((?:\[!b:[^\]]+\]\s*)+)")

    def _get_image_data(self, blip_id):
        """Retrieves raw binary data of an image using its Relationship ID (rId)."""
        try:
            part = self.doc.part.related_parts[blip_id]
            return part.blob
        except Exception:
            return None

    def _is_label(self, text):
        """Checks if a piece of text is a question or option label that shouldn't be bolded."""
        if not text:
            return False
        return bool(self.ignore_bold_pattern.match(text.strip()))

    def _process_run(self, run, paragraph) -> str:
        """
        Processes a 'Run' (a contiguous block of text with the same formatting).
        Steps:
        1. Look for Images (Drawing elements).
        2. Look for Math elements (oMath or embedded objects).
        3. Identify Bold text (mark it with [!b:...] for later cleaning).
        """
        text = run.text

        # 1. IMAGE Processing
        # Search for inline or floating drawings.
        drawings = run._element.findall(".//w:drawing", namespaces=nsmap)
        for drawing in drawings:
            blips = drawing.findall(".//a:blip", namespaces=nsmap)
            for blip in blips:
                rId = blip.get(f"{{{nsmap['r']}}}embed")
                if rId:
                    img_bytes = self._get_image_data(rId)
                    if img_bytes:
                        self.img_count += 1
                        img_id = f"img_{self.img_count}"

                        # Convert to PNG for web compatibility.
                        src = self.image_processor.convert_image_to_png(
                            img_bytes, img_id
                        )

                        self.assets[img_id] = {"type": "image", "src": src}
                        # Inject a specific placeholder tag for the frontend.
                        return f"[img:${img_id}$]"

        # 2. MATH Processing
        # Check if the run contains Microsoft Office Math Markup (OMML).
        if run._element.findall(".//m:oMath", namespaces=nsmap) or run._element.findall(
            ".//w:object", namespaces=nsmap
        ):
            self.math_count += 1
            math_id = f"mathtype_{self.math_count}"

            # Convert OMML to LaTeX string.
            latex_str = self.math_processor.extract_latex_from_run(run._element)
            img_src = None

            # Fallback for old Equation objects (MathType): Extract as image if LaTeX fails.
            if not latex_str:
                objects = run._element.findall(".//w:object", namespaces=nsmap)
                for obj in objects:
                    res = self.math_processor.extract_ole_image_bytes(
                        obj, self._get_image_data
                    )
                    if res:
                        img_bytes, rId = res
                        img_src = self.image_processor.convert_image_to_png(
                            img_bytes, math_id
                        )
                        break

            self.assets[math_id] = {
                "type": "math",
                "latex": latex_str,
                "src": img_src,
                "placeholder": f"[{math_id}]",
            }
            return f"[!m:${math_id}$]"

        # 3. BOLD Text Marking
        # Wrap bold text in a tag. We'll decide whether to keep it later
        # (e.g., labels like "Câu 1" shouldn't stay bold).
        if run.bold and text.strip():
            return f"[!b:{text}]"

        return text

    def _clean_bold_labels(self, text):
        """
        Post-processing for bold tags. If a group of bold tags represents a
        label like "Câu 1." or "A.", it removes the bold formatting.
        """

        def replacer(match):
            full_str = match.group(1)
            # Remove the marking tags to get raw text.
            raw_text = re.sub(r"\[!b:|\]", "", full_str)

            if self._is_label(raw_text):
                return raw_text  # Clean formatting.
            else:
                return full_str  # Keep bold.

        return self.bold_chain_pattern.sub(replacer, text)

    def _process_inline_latex_text(self, text):
        """
        Detects hand-written LaTeX like '$...$' in text and converts it
        to a structured math asset.
        """
        if "$" not in text:
            return text

        existing_tags = []

        def mask_tag(match):
            tag = match.group(0)
            existing_tags.append(tag)
            return f"__MATH_TAG_{len(existing_tags) - 1}__"

        try:
            # Step 1: Hide existing tags so we don't double-process them.
            temp_text = re.sub(r"(\[!m:[^\]]+\$\]|\[img:\$[^\]]+\$\])", mask_tag, text)

            # Step 2: Replace $...$ with structured [!m:...] tags.
            def replace_latex(match):
                latex_content = match.group(1)
                if not latex_content.strip():
                    return match.group(0)

                self.math_count += 1
                math_id = f"mathtype_{self.math_count}"

                self.assets[math_id] = {
                    "type": "math",
                    "latex": latex_content,
                    "src": None,
                    "placeholder": "[Formula]",
                }
                return f"[!m:${math_id}$]"

            temp_text = re.sub(r"\$([^\$]+)\$", replace_latex, temp_text)

            # Step 3: Put internal tags back.
            for i, tag in enumerate(existing_tags):
                temp_text = temp_text.replace(f"__MATH_TAG_{i}__", tag)

            return temp_text

        except Exception as e:
            print(f"Inline latex processing error: {e}")
            return text

    def _process_paragraph(self, paragraph) -> str:
        """
        Aggregates Runs into a line of text, processes OMML, and handles Auto-Marking.
        """
        line_content = ""
        para_xml = paragraph._element
        run_map = {id(run._element): run for run in paragraph.runs}

        # Iterate through paragraph children (Runs AND Math elements) in order.
        for child in para_xml:
            tag = etree.QName(child.tag).localname if child.tag else ""

            # Case 1: Display Math (paragraphs that ARE formulas).
            if tag in ("oMathPara", "oMath"):
                latex_str = self.math_processor.process_omml_element(child)
                if latex_str:
                    self.math_count += 1
                    math_id = f"mathtype_{self.math_count}"
                    self.assets[math_id] = {
                        "type": "math",
                        "latex": latex_str,
                        "placeholder": f"[{math_id}]",
                    }
                    line_content += f"[!m:${math_id}$]"

            # Case 2: Standard Text Runs.
            elif tag == "r":
                run = run_map.get(id(child))
                if run:
                    line_content += self._process_run(run, paragraph)

        # Apply post-processing (Inline $LaTeX$, Remove Bold Labels).
        line_content = self._process_inline_latex_text(line_content)
        line_content = self._clean_bold_labels(line_content)

        # --- AUTO-MARKING LOGIC ---
        # 1. Identify current question number to track progress.
        clean_text = re.sub(r"\[![a-z]:|\]", "", line_content).strip()
        q_match = self.q_num_pattern.match(clean_text)
        if q_match:
            try:
                self.current_q_num = int(q_match.group(1))
                self.global_q_counter += 1
            except Exception:
                pass

        # 2. Match current line against the Provided Answer Key.
        if self.global_q_counter and self.global_q_counter in self.answer_map:
            correct_val = self.answer_map[self.global_q_counter]
            correct_chars = [c.strip().upper() for c in correct_val.split(",")]

            opt_match = self.opt_pattern.match(clean_text)
            if opt_match:
                opt_char = opt_match.group(1).upper()
                if opt_char in correct_chars:
                    # Insert the '*' marking character for the frontend to highlight.
                    if not re.search(r"\*" + opt_char, line_content, re.IGNORECASE):
                        line_content = re.sub(
                            r"(^|\s)(" + opt_char + r")([.\)])",
                            r"\1*\2\3",
                            line_content,
                            count=1,
                            flags=re.IGNORECASE,
                        )

        return line_content

    def _process_table(self, table) -> str:
        """
        Converts a Word table into specialized text formats.
        - 'Layout tables' (shuffling columns) -> Flattened into lines.
        - 'Data tables' (statistical tables) -> Kept in a [* Col 1 | Col 2 *] format.
        """
        num_rows = len(table.rows) if table.rows else 0
        max_cols = max(len(row.cells) for row in table.rows) if table.rows else 0

        # Heuristic: Determine if it's a real data table or just a layout container.
        is_data_table = (num_rows >= 2 and max_cols >= 3) or (
            num_rows >= 3 and max_cols >= 2
        )

        lines = []
        for row in table.rows:
            cells_txt = []
            for cell in row.cells:
                cell_content = " ".join(
                    [self._process_paragraph(p) for p in cell.paragraphs]
                )
                cells_txt.append(cell_content.strip())

            if is_data_table:
                # Store as a structured string for the editor.
                row_str = "[* " + " | ".join(cells_txt) + " *]"
                lines.append(row_str)
            else:
                # Layout table: just unpack contents.
                for txt in cells_txt:
                    if txt.strip():
                        lines.append(txt)

        return "\n".join(lines)

    def serialize(self) -> dict:
        """
        Main entry point. Iterates through the document body and returns
        the full text and collected assets (images/formulas).
        """
        raw_lines = []
        inline_ans_pattern = re.compile(
            r"^(?:Đáp án|ĐÁP ÁN|Dap an)[:\.]", re.IGNORECASE
        )

        for child in self.doc.element.body.iterchildren():
            txt = ""
            if isinstance(child, CT_P):
                para = Paragraph(child, self.doc)
                txt = self._process_paragraph(para)
            elif isinstance(child, CT_Tbl):
                table = Table(child, self.doc)
                txt = self._process_table(table)

            if txt.strip():
                # Fix: If the "Finish" line appears BEFORE an inline answer, swap them
                # to maintain the correct document structure.
                if raw_lines:
                    last_line = raw_lines[-1]
                    clean_last = re.sub(r"\[![a-z]:|\]", "", last_line).strip()
                    clean_txt = re.sub(r"\[![a-z]:|\]", "", txt).strip()

                    if "HẾT" in clean_last.upper():
                        if inline_ans_pattern.match(clean_txt):
                            raw_lines.insert(-1, txt)
                            continue

                raw_lines.append(txt)

        return {"raw_text": "\n".join(raw_lines), "assets_map": self.assets}
