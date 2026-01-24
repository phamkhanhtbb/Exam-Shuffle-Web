"""
Core logic V7.0: Performance Optimized (Split Parse & Gen)
"""
from __future__ import annotations
import io
import random
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional

from docx import Document
from docx.document import Document as _Document
from docx.oxml import OxmlElement
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.table import Table
from docx.shared import RGBColor

# --- Giữ nguyên các REGEX và Dataclass như cũ ---
SECTION_PATTERN = re.compile(r"^\s*PH[ẦA]N\s+([IVX0-9]+)", re.IGNORECASE)
QUESTION_PATTERN = re.compile(r"^\s*(?:Cau|C e2u|Bai|B e0i|Câu|Bài)\s+(\d+)", re.IGNORECASE)
OPTION_PATTERN = re.compile(r"^\s*([ABCD])\s*[\.|\)]\s*")
SUB_OPTION_PATTERN = re.compile(r"^\s*([a-d])\s*[\)|\.]\s*")
HEADER_KEYWORD_PATTERN = re.compile(r"(Mã\s*đề)", re.IGNORECASE)
END_NOTE_PATTERN = re.compile(r"^\s*[-]*\s*(HẾT|GIÁM THỊ|GHI CHÚ)\s*[-]*", re.IGNORECASE)


@dataclass
class OptionBlock:
    label: str
    elements: List[OxmlElement] = field(default_factory=list)
    is_correct: bool = False


@dataclass
class QuestionBlock:
    ordinal: int
    raw_label: str
    stem_elements: List[OxmlElement] = field(default_factory=list)
    options: List[OptionBlock] = field(default_factory=list)
    mode: str = "mcq"


@dataclass
class Section:
    title: str
    info_elements: List[OxmlElement] = field(default_factory=list)
    questions: List[QuestionBlock] = field(default_factory=list)


@dataclass
class ExamStructure:
    header_elements: List[OxmlElement] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    footer_elements: List[OxmlElement] = field(default_factory=list)


# --- Giữ nguyên các hàm Helper: _iter_block_items, _get_text, _smart_replace_start... ---
# (Để tiết kiệm không gian, tôi giả định bạn giữ nguyên các hàm helper từ phiên bản cũ)
# ... [Insert Helper Functions Here] ...

def _iter_block_items(doc: _Document):
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield "p", Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield "tbl", Table(child, doc)


def _get_text(block: Union[Paragraph, Table]) -> str:
    if isinstance(block, Paragraph): return block.text or ""
    return ""


def _clear_body_keep_sectpr(doc: _Document) -> Optional[OxmlElement]:
    body = doc.element.body
    sect_pr = None
    for child in list(body.iterchildren()):
        if child.tag.endswith("sectPr"):
            sect_pr = child
            continue
        body.remove(child)
    return sect_pr


def _append_element(body: OxmlElement, sect_pr: Optional[OxmlElement], element: OxmlElement) -> None:
    if sect_pr is not None:
        sect_pr.addprevious(element)
    else:
        body.append(element)


# --- Các hàm xử lý Header/Option giữ nguyên ---
# ... [Insert _replace_code_in_paragraph, _recursive_replace_code_smart, _relabel_stem, etc.] ...
# (Copy các hàm logic xử lý text từ file cũ sang đây)

def _smart_replace_start(paragraph: Paragraph, regex_pattern: re.Pattern, new_prefix: str):
    full_text = paragraph.text
    match = regex_pattern.match(full_text)
    if not match:
        if paragraph.runs:
            paragraph.runs[0].text = new_prefix + paragraph.runs[0].text
        else:
            paragraph.add_run(new_prefix)
        return
    len_to_remove = len(match.group(0))
    current_idx = 0
    replacement_done = False
    for run in paragraph.runs:
        run_text = run.text
        if not run_text: continue
        run_len = len(run_text)
        if current_idx < len_to_remove:
            remove_in_this_run = min(run_len, len_to_remove - current_idx)
            remainder = run_text[remove_in_this_run:]
            if not replacement_done:
                run.text = new_prefix + remainder
                replacement_done = True
            else:
                run.text = remainder
            current_idx += run_len
        else:
            break


def _is_run_correct_marker(run: Run) -> bool:
    if run.underline is not None and run.underline is not False and run.underline != 0: return True
    if run.font.highlight_color: return True
    return False


def _remove_answer_markers(paragraph: Paragraph):
    for run in paragraph.runs:
        run.underline = False
        run.font.underline = False
        if run.font.color and run.font.color.rgb: run.font.color.rgb = RGBColor(0, 0, 0)
        if run.font.highlight_color: run.font.highlight_color = None


def _check_if_correct(elements: List[OxmlElement]) -> bool:
    for el in elements:
        if isinstance(el, CT_P):
            p = Paragraph(el, None)
            for run in p.runs:
                if _is_run_correct_marker(run): return True
    return False


def _replace_code_in_paragraph(p: Paragraph, new_code: str) -> bool:
    text = p.text
    if "Mã đề" in text or "MÃ ĐỀ" in text:
        num_match = re.search(r"\d+", text)
        if num_match:
            old_num = num_match.group(0)
            for run in p.runs:
                if old_num in run.text:
                    run.text = run.text.replace(old_num, new_code)
                    return True
            p.text = text.replace(old_num, new_code)
            return True
        else:
            p.add_run(f" {new_code}")
            return True
    return False


def _recursive_replace_code_smart(element, new_code: str) -> bool:
    found = False
    if isinstance(element, CT_P):
        found = _replace_code_in_paragraph(Paragraph(element, None), new_code)
    elif isinstance(element, CT_Tbl):
        table = Table(element, None)
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if _replace_code_in_paragraph(paragraph, new_code): found = True
    return found


def _parse_options(chunk_elements: List[Tuple[str, object]]) -> Tuple[str, List[OxmlElement], List[OptionBlock]]:
    opt_indices = []
    for idx, (kind, block) in enumerate(chunk_elements):
        if kind == "p":
            text = _get_text(block).strip()
            if OPTION_PATTERN.match(text):
                opt_indices.append((idx, OPTION_PATTERN.match(text).group(1).upper(), "mcq"))
            elif SUB_OPTION_PATTERN.match(text):
                opt_indices.append((idx, SUB_OPTION_PATTERN.match(text).group(1).lower(), "true_false"))
    if not opt_indices: return "short", [blk._element for _, blk in chunk_elements], []
    first_type = opt_indices[0][2]
    valid_indices = [x for x in opt_indices if x[2] == first_type]
    first_opt_idx = valid_indices[0][0]
    stems = [blk._element for _, blk in chunk_elements[:first_opt_idx]]
    options = []
    split_points = [x[0] for x in valid_indices] + [len(chunk_elements)]
    for i, (start_idx, label, _) in enumerate(valid_indices):
        end_idx = split_points[i + 1]
        opt_elems = [blk._element for _, blk in chunk_elements[start_idx:end_idx]]
        is_correct = _check_if_correct(opt_elems)
        options.append(OptionBlock(label, opt_elems, is_correct))
    return first_type, stems, options


def _parse_questions_in_range(blocks: List[Tuple[str, object]]) -> List[QuestionBlock]:
    if not blocks: return []
    q_indices = []
    for idx, (kind, block) in enumerate(blocks):
        text = _get_text(block)
        if QUESTION_PATTERN.match(text): q_indices.append(idx)
    if not q_indices: return []
    questions = []
    for i, start in enumerate(q_indices):
        next_q_start = q_indices[i + 1] if i + 1 < len(q_indices) else len(blocks)
        raw_chunk = blocks[start:next_q_start]
        actual_end = len(raw_chunk)
        for sub_idx, (kind, block) in enumerate(raw_chunk):
            if END_NOTE_PATTERN.match(_get_text(block)):
                actual_end = sub_idx
                break
        clean_chunk = raw_chunk[:actual_end]
        if not clean_chunk: continue
        first_text = _get_text(clean_chunk[0][1])
        match = QUESTION_PATTERN.match(first_text)
        raw_label = match.group(0) if match else "Câu ?"
        mode, stems, opts = _parse_options(clean_chunk)
        questions.append(QuestionBlock(0, raw_label, stems, opts, mode))
    return questions


def parse_structure(doc: _Document) -> ExamStructure:
    blocks = list(_iter_block_items(doc))
    structure = ExamStructure()
    footer_start_idx = len(blocks)
    for idx, (kind, block) in enumerate(blocks):
        if END_NOTE_PATTERN.search(_get_text(block)):
            footer_start_idx = idx
            break
    main_blocks = blocks[:footer_start_idx]
    structure.footer_elements = [blk._element for _, blk in blocks[footer_start_idx:]]
    section_starts = []
    for idx, (kind, block) in enumerate(main_blocks):
        if SECTION_PATTERN.match(_get_text(block)): section_starts.append(idx)
    if not section_starts:
        first_q_idx = 0
        for idx, (kind, block) in enumerate(main_blocks):
            if QUESTION_PATTERN.match(_get_text(block)):
                first_q_idx = idx
                break
        structure.header_elements = [blk._element for _, blk in main_blocks[:first_q_idx]]
        default_section = Section("", [], _parse_questions_in_range(main_blocks[first_q_idx:]))
        structure.sections.append(default_section)
    else:
        structure.header_elements = [blk._element for _, blk in main_blocks[:section_starts[0]]]
        for i, start_idx in enumerate(section_starts):
            end_idx = section_starts[i + 1] if i + 1 < len(section_starts) else len(main_blocks)
            section_blocks = main_blocks[start_idx:end_idx]
            title = _get_text(section_blocks[0][1])
            q_start = len(section_blocks)
            for j, (kind, blk) in enumerate(section_blocks):
                if j == 0: continue
                if QUESTION_PATTERN.match(_get_text(blk)):
                    q_start = j
                    break
            info = [blk._element for _, blk in section_blocks[1:q_start]]
            qs = _parse_questions_in_range(section_blocks[q_start:])
            structure.sections.append(Section(title, info, qs))
    return structure


def _relabel_stem(elements: List[OxmlElement], new_ord: int):
    first_para = None
    for el in elements:
        if isinstance(el, CT_P):
            first_para = Paragraph(el, None)
            break
    if first_para is None: return
    text = first_para.text
    match = QUESTION_PATTERN.match(text)
    separator = ":"
    if match:
        old_label = match.group(0)
        if "." in old_label:
            separator = "."
        elif ":" in old_label:
            separator = ":"
    new_prefix = f"Câu {new_ord}{separator} "
    EXTENDED_CLEAN_PATTERN = re.compile(r"^\s*(?:Cau|C e2u|Bai|B e0i|Câu|Bài)\s+\d+\s*[:.]?\s*[:.]?\s*", re.IGNORECASE)
    _smart_replace_start(first_para, EXTENDED_CLEAN_PATTERN, new_prefix)


def _relabel_and_clean_options(options: List[OptionBlock], mode: str):
    if mode == "mcq":
        labels = [chr(ord('A') + i) for i in range(len(options))]
        tmpl = "{}. "
        pat = OPTION_PATTERN
    elif mode == "true_false":
        labels = [chr(ord('a') + i) for i in range(len(options))]
        tmpl = "{}) "
        pat = SUB_OPTION_PATTERN
    else:
        return
    for opt, lbl in zip(options, labels):
        opt.label = lbl
        if not opt.elements: continue
        for el in opt.elements:
            if isinstance(el, CT_P): _remove_answer_markers(Paragraph(el, None))
        first = opt.elements[0]
        if isinstance(first, CT_P):
            _smart_replace_start(Paragraph(first, None), pat, tmpl.format(lbl))


# --- POINT 5: TÁCH LOGIC PARSE VÀ GENERATE ---

def parse_exam_template(source_bytes: bytes) -> ExamStructure:
    """Chỉ gọi hàm này 1 lần."""
    doc = Document(io.BytesIO(source_bytes))
    return parse_structure(doc)


def generate_variant_from_structure(source_bytes: bytes, structure: ExamStructure, seed: int, exam_code: str,
                                    shuffle_questions: bool = True, shuffle_options: bool = True) -> Tuple[
    bytes, List[str]]:
    """Gọi hàm này N lần, tái sử dụng structure."""
    rng = random.Random(seed)

    # Tạo document mới làm canvas (cần source_bytes để lấy style gốc)
    target = Document(io.BytesIO(source_bytes))
    sect_pr = _clear_body_keep_sectpr(target)
    body = target.element.body

    # 1. HEADER (Deepcopy từ structure đã parse)
    for el in structure.header_elements:
        clone = deepcopy(el)
        _recursive_replace_code_smart(clone, exam_code)
        _append_element(body, sect_pr, clone)

    correct_answers = []

    # 2. SECTIONS & QUESTIONS
    for sec in structure.sections:
        if sec.title:
            p = target.add_paragraph()
            r = p.add_run(sec.title)
            r.bold = True
            _append_element(body, sect_pr, p._element)

        for el in sec.info_elements:
            _append_element(body, sect_pr, deepcopy(el))

        # Shallow copy list để shuffle không ảnh hưởng structure gốc
        qs = list(sec.questions)
        if shuffle_questions:
            rng.shuffle(qs)

        for i, q in enumerate(qs, start=1):
            new_q = deepcopy(q)  # Deep copy để sửa label mà không hỏng gốc
            _relabel_stem(new_q.stem_elements, i)

            if shuffle_options and new_q.options:
                rng.shuffle(new_q.options)

            _relabel_and_clean_options(new_q.options, new_q.mode)

            if new_q.mode == "mcq":
                ans = next((opt.label for opt in new_q.options if opt.is_correct), "")
                correct_answers.append(ans)

            for el in new_q.stem_elements:
                _append_element(body, sect_pr, el)
            for opt in new_q.options:
                for el in opt.elements:
                    _append_element(body, sect_pr, el)

    # 3. FOOTER
    for el in structure.footer_elements:
        _append_element(body, sect_pr, deepcopy(el))

    buf = io.BytesIO()
    target.save(buf)
    buf.seek(0)
    return buf.getvalue(), correct_answers