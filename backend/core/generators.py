from copy import deepcopy
import random
import re
import io
from typing import Tuple, List, Optional
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
import logging
logger = logging.getLogger("worker")

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

            # Shuffle Options (MCQ and True/False)
            if shuffle_options and new_q.options and new_q.mode in ('mcq', 'true_false'):
                rng.shuffle(new_q.options)

            # Process Options & Record Answers (logic khớp với server.py export_excel_key)
            current_ans = ""

            if new_q.mode == 'mcq':
                labels = ["A", "B", "C", "D", "E", "F"]
                mcq_corrects = []
                for i, opt in enumerate(new_q.options):
                    if i >= len(labels): break
                    new_lbl = labels[i]
                    if opt.is_correct: mcq_corrects.append(new_lbl)

                    _process_mcq_option_format(opt, new_lbl)
                
                # Match Excel gốc: chỉ lấy đáp án đầu tiên cho MCQ
                current_ans = mcq_corrects[0] if mcq_corrects else ""
            
            elif new_q.mode == 'true_false':
                # Logic for True/False: Re-label after shuffle and track correct
                # Format: Đ = Đúng, S = Sai (e.g., ĐSĐĐ means a=True, b=False, c=True, d=True)
                labels_tf = ["a", "b", "c", "d", "e"]
                tf_result = []
                for i, opt in enumerate(new_q.options):
                    if i >= len(labels_tf): break
                    new_lbl = labels_tf[i]
                    # Đ = correct, S = incorrect
                    tf_result.append("Đ" if opt.is_correct else "S")
                    # Update option label to new position (for rendering)
                    opt.label = new_lbl
                current_ans = "".join(tf_result)
            
            # Short Answer / Fallback (khớp với server.py)
            if not current_ans and new_q.correct_answer_text:
                current_ans = new_q.correct_answer_text
            
            # LUÔN append để giữ đúng index (như Excel gốc server.py:467)
            final_answers.append(current_ans)

            # Render Stem & Options
            for el in new_q.stem_elements: _append_element(body, sect_pr, el)
            for opt in new_q.options:
                for el in opt.elements: _append_element(body, sect_pr, el)
            
            global_q_idx += 1
            
    return global_q_idx, final_answers


def _apply_external_key(structure: ExamStructure, external_map: dict):
    """Override is_correct flags based on external Answer Key (from Editor)."""
    if not external_map: return
    
    logger.info(f"Applying External Key Map: {len(external_map)} entries.")
    matched_count = 0
    
    for sec in structure.sections:
        for q in sec.questions:
            # Fix: Convert original_idx to string because JSON keys are always strings
            q_idx_str = str(q.original_idx)
            
            # Determine Key to use
            key_to_use = None
            if q.content_hash and q.content_hash in external_map:
                key_to_use = q.content_hash
                logger.debug(f"Matched Q{q.original_idx} by HASH: {q.content_hash}")
            elif q_idx_str in external_map:
                key_to_use = q_idx_str
                logger.debug(f"Matched Q{q.original_idx} by INDEX: {q_idx_str}")
            
            if key_to_use:
                matched_count += 1
                # Found an entry for this question
                answer_value = str(external_map[key_to_use]).strip()
                
                # Determine if this is MCQ/TF (single letters like "A", "B,C") or Short Answer (numeric/text)
                # Check if answer_value looks like option labels
                is_option_answer = bool(re.match(r'^[A-Za-z](,[A-Za-z])*$', answer_value.replace(' ', '')))
                
                if is_option_answer and q.options:
                    # MCQ or True/False: Set is_correct on matching options
                    correct_lbl = answer_value.upper()
                    targets = [x.strip() for x in correct_lbl.split(',')]
                    
                    # Reset all to False first
                    for opt in q.options:
                        opt.is_correct = False
                        
                    # Set True for targets
                    for opt in q.options:
                        clean_lbl = ""
                        for char in opt.label:
                            if char.isalpha():
                                clean_lbl = char.upper()
                                break
                        
                        if clean_lbl in targets:
                             opt.is_correct = True
                else:
                    # Short Answer: Set correct_answer_text directly
                    q.correct_answer_text = answer_value
                    logger.debug(f"Q{q.original_idx}: Set Short Answer = {answer_value}")
            else:
                logger.debug(f"Q{q.original_idx}: No external key found.")

    logger.info(f"External Key Application Complete. Matched {matched_count} questions.")


def generate_variant_from_structure(
        source_bytes: bytes, structure: ExamStructure, seed: int, exam_code: str,
        shuffle_questions: bool = True, shuffle_options: bool = True,
        external_answer_map: Optional[dict] = None
) -> Tuple[bytes, List[str]]:
    
    # Clone structure to avoid side effects on other variants if modified?
    # Actually structure is parsed once. If we modify it based on external map, 
    # we should modify it ONCE before loop, or work on a copy.
    # The external map is the TRUTH for ALL variants. So we can modify it once.
    # BUT generators might be called in parallel or sequentially.
    # Ideally, apply it outside this function? Or inside?
    # If we apply it inside, we should deepcopy. 
    # But wait, 'structure' passed here IS the template.
    # If we modify it permanently, it's fine because the map applies to the whole job.
    # However, safe practice: modify matching copy.
    
    # Optimization: If we trust the structure is fresh or reused correctly.
    # Let's apply it if provided.
    if external_answer_map:
        _apply_external_key(structure, external_answer_map)

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
    
    return buf.getvalue(), final_answers
