from copy import deepcopy
import random
import re
import io
from typing import Tuple, List
from docx import Document
from docx.oxml import OxmlElement, ns
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph

from .constants import OPTION_START_PATTERN
from .models import OptionBlock, ExamStructure
from .utils import (
    _recursive_replace_code, _append_element, _clear_body_keep_sectpr,
    _smart_replace_start, _create_simple_para_element, _normalize_format_and_clean
)

def _build_exam_header(body, sect_pr, header_elements, exam_code):
    """Clone header elements and replace exam code."""
    for el in header_elements:
        clone = deepcopy(el)
        _recursive_replace_code(clone, exam_code)
        _append_element(body, sect_pr, clone)

def _build_exam_footer(body, sect_pr, footer_elements):
    """Clone footer elements."""
    for el in footer_elements:
        _append_element(body, sect_pr, deepcopy(el))

def _process_mcq_option_format(opt: OptionBlock, new_lbl: str):
    """Normalize format for MCQ options (Bold label A. B. C. D.)"""
    first_el = opt.elements[0]
    if isinstance(first_el, CT_P):
        p = Paragraph(first_el, None)
        _normalize_format_and_clean(p)  # Clean format cũ

        if OPTION_START_PATTERN.match(p.text):
            # Trường hợp text thuần túy đã có nhãn cũ (C. ...) -> Thay thế
            _smart_replace_start(p, OPTION_START_PATTERN, f"{new_lbl}. ")
            if p.runs: p.runs[0].font.bold = True
        else:
            # Trường hợp Rich Text (công thức) chưa có nhãn
            # 1. Tạo phần tử Run (<w:r>)
            r = OxmlElement('w:r')
            # 2. Tạo Properties cho Run (để set in đậm)
            rPr = OxmlElement('w:rPr')
            b = OxmlElement('w:b')
            rPr.append(b)
            r.append(rPr)
            # 3. Tạo phần tử Text (<w:t>)
            t = OxmlElement('w:t')
            t.set(ns.qn('xml:space'), 'preserve')  # Giữ khoảng trắng
            t.text = f"{new_lbl}. "
            r.append(t)
            # 4. Chèn Run mới tạo vào vị trí đầu tiên của Paragraph (<w:p>)
            p._element.insert(0, r)

    # Xử lý các đoạn văn còn lại của option (nếu có)
    for el in opt.elements[1:]:
        if isinstance(el, CT_P): _normalize_format_and_clean(Paragraph(el, None))

def _build_exam_body(body, sect_pr, target_doc, structure, seed, shuffle_questions=True, shuffle_options=True) -> Tuple[int, List[str]]:
    """Build the main content of the exam (Sections -> Questions)."""
    rng = random.Random(seed)
    final_answers = []
    global_q_idx = 1
    
    for sec in structure.sections:
        # 1. Section Title
        if sec.title:
            p = target_doc.add_paragraph()
            r = p.add_run(sec.title)
            r.bold = True
            _append_element(body, sect_pr, p._element)

        # 2. Section Info
        for el in sec.info_elements:
            _append_element(body, sect_pr, deepcopy(el))

        # 3. Questions
        qs = list(sec.questions)
        if shuffle_questions: rng.shuffle(qs)

        for q in qs:
            new_q = deepcopy(q)
            # Re-label question stem
            new_prefix = f"Câu {global_q_idx}: "
            replaced_label = False
            for el in new_q.stem_elements:
                if isinstance(el, CT_P):
                    p = Paragraph(el, None)
                    # Use standard pattern for replacement
                    pat = re.compile(r"^\s*(?:Cau|Câu|Bai|Bài)\s+\d+[:.]?\s*", re.IGNORECASE)
                    if pat.match(p.text):
                        _smart_replace_start(p, pat, new_prefix)
                        replaced_label = True
                        break
            if not replaced_label:
                p_new = _create_simple_para_element(new_prefix)
                new_q.stem_elements.insert(0, p_new)

            # Shuffle Options
            if shuffle_options and new_q.options and new_q.mode == 'mcq':
                rng.shuffle(new_q.options)

            # Process Options & Record Answers
            if new_q.mode == 'mcq':
                labels = ["A", "B", "C", "D", "E", "F"]
                for i, opt in enumerate(new_q.options):
                    if i >= len(labels): break
                    new_lbl = labels[i]
                    if opt.is_correct: final_answers.append(new_lbl)

                    _process_mcq_option_format(opt, new_lbl)
            
            elif new_q.mode == 'true_false':
                # Logic for True/False (keep original labels a, b, c...)
                 for i, opt in enumerate(new_q.options):
                    if opt.is_correct: final_answers.append(opt.label) # Save 'a', 'b'...
            
            elif new_q.mode == 'short':
                 # For short answer, we don't shuffle (no options).
                 pass

            # Render Stem & Options
            for el in new_q.stem_elements: _append_element(body, sect_pr, el)
            for opt in new_q.options:
                for el in opt.elements: _append_element(body, sect_pr, el)
            
            global_q_idx += 1
            
    return global_q_idx, final_answers


def generate_variant_from_structure(
        source_bytes: bytes, structure: ExamStructure, seed: int, exam_code: str,
        shuffle_questions: bool = True, shuffle_options: bool = True
) -> Tuple[bytes, List[str]]:
    
    target = Document(io.BytesIO(source_bytes))
    sect_pr = _clear_body_keep_sectpr(target)
    body = target.element.body

    # 1. Header
    _build_exam_header(body, sect_pr, structure.header_elements, exam_code)

    # 2. Body
    global_q_idx, final_answers = _build_exam_body(
        body, sect_pr, target, structure, seed, shuffle_questions, shuffle_options
    )

    # 3. Footer
    _build_exam_footer(body, sect_pr, structure.footer_elements)

    # Save
    buf = io.BytesIO()
    target.save(buf)
    buf.seek(0)
    
    # Pad answers if missing
    while len(final_answers) < (global_q_idx - 1): final_answers.append("X")
    
    return buf.getvalue(), final_answers
