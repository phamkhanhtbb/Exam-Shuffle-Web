import io
import re
from typing import List, Tuple, Dict
from docx import Document
from docx.oxml import OxmlElement

# Import internal modules
from .constants import (
    SECTION_PATTERN, QUESTION_PATTERN, OPTION_START_PATTERN,
    INLINE_OPTION_PATTERN, SUB_OPTION_PATTERN, END_NOTE_PATTERN, ANSWER_HEADER_PATTERN
)
from .models import OptionBlock, QuestionBlock, Section, ExamStructure
from .utils import (
    _iter_block_items, _get_text, _build_paragraph_mask, _slice_paragraph_runs
)
from exceptions import AnswerKeyNotFoundError, EmptyQuestionError

# Note: _split_inline_options_smart logic was partly in utils and partly inline in original file.
# I will implement _split_inline_options_smart fully here or rely on utils.
# In utils above, I created _build_paragraph_mask. I need _split_inline_options_smart in utils or here.
# Let's check utils again... I didn't put _split_inline_options_smart in utils content.
# Only _build_paragraph_mask. 
# So I should implement _split_inline_options_smart here using _build_paragraph_mask from utils.

def _split_inline_options_smart(paragraph) -> List[dict]:
    full_text, mask = _build_paragraph_mask(paragraph)
    matches = list(INLINE_OPTION_PATTERN.finditer(full_text))
    if not matches: return []
    results = []
    for i, match in enumerate(matches):
        label = match.group(1).upper()
        start_idx = match.start()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        rich_element = _slice_paragraph_runs(paragraph, start_idx, end_idx)
        label_char_idx = match.start(1)
        is_marked = False
        if label_char_idx < len(mask) and mask[label_char_idx]:
            is_marked = True
        elif any(mask[start_idx:end_idx]):
            is_marked = True
        results.append({"label": label, "element": rich_element, "is_marked": is_marked})
    return results

# Fix import in utils: _slice_paragraph_runs is in utils.
from .utils import _slice_paragraph_runs


def _extract_answers_from_blocks(blocks: List[Tuple[str, object]]) -> Dict[int, str]:
    """Quét đáp án từ một list các block (dùng cho phần ĐÁP ÁN bị cắt ra)"""
    answers_map = {}
    q_pat = re.compile(r"^\s*(?:Câu)?\s*(\d+)[\.:]?\s*$")
    a_pat = re.compile(r"^\s*([A-D])\s*$")

    for kind, block in blocks:
        if kind == 'tbl':
            table = block
            # Chiến thuật 1: Hàng ngang (Matrix)
            rows = table.rows
            for r in range(len(rows) - 1):
                row_q = rows[r]
                row_a = rows[r + 1]
                valid_pairs = 0
                temp_row_map = {}
                min_cells = min(len(row_q.cells), len(row_a.cells))
                for c in range(min_cells):
                    txt_q = row_q.cells[c].text.strip()
                    txt_a = row_a.cells[c].text.strip()
                    q_match = q_pat.match(txt_q)
                    a_match = a_pat.match(txt_a)
                    if q_match and a_match:
                        try:
                            temp_row_map[int(q_match.group(1))] = a_match.group(1).upper()
                            valid_pairs += 1
                        except:
                            pass
                if valid_pairs >= 3:
                    answers_map.update(temp_row_map)
                    continue

            # Chiến thuật 2: Cặp dọc/liền kề
            cells = [cell.text.strip() for row in table.rows for cell in row.cells]
            idx = 0
            while idx < len(cells) - 1:
                curr, nxt = cells[idx], cells[idx + 1]
                q_match, a_match = q_pat.match(curr), a_pat.match(nxt)
                if q_match and a_match:
                    try:
                        q_num = int(q_match.group(1))
                        if q_num not in answers_map:
                            answers_map[q_num] = a_match.group(1).upper()
                        idx += 2
                    except:
                        idx += 1
                else:
                    idx += 1
    return answers_map


def _parse_mcq_options(chunk_elements: List[Tuple[str, object]]) -> List[OptionBlock]:
    """Parse multiple choice options (A. B. C. D.)"""
    options = []
    opt_indices = []
    
    # 1. First pass: Find lines starting with A., B., etc.
    for idx, (kind, block) in enumerate(chunk_elements):
         if kind == "p":
             text = _get_text(block).strip()
             match = OPTION_START_PATTERN.match(text)
             if match:
                 opt_indices.append((idx, match.group(1).upper()))
    
    if not opt_indices:
        return []

    # 2. Slice blocks based on indices
    split_points = [x[0] for x in opt_indices] + [len(chunk_elements)]
    for i, (start_idx, label) in enumerate(opt_indices):
        end_idx = split_points[i + 1]
        opt_elems = [blk._element for _, blk in chunk_elements[start_idx:end_idx]]
        
        # Check marking (red/underline)
        is_marked = False
        for blk_idx in range(start_idx, end_idx):
            kind, blk = chunk_elements[blk_idx]
            if kind == 'p' and any(_build_paragraph_mask(blk)[1]):
                is_marked = True
                break
        options.append(OptionBlock(label, opt_elems, is_marked))
        
    return options

def _parse_tf_options(chunk_elements: List[Tuple[str, object]]) -> List[OptionBlock]:
    """Parse True/False options (a) b) c) d))"""
    options = []
    opt_indices = []
    
    for idx, (kind, block) in enumerate(chunk_elements):
         if kind == "p":
             text = _get_text(block).strip()
             match = SUB_OPTION_PATTERN.match(text)
             if match:
                 opt_indices.append((idx, match.group(1).lower()))
                 
    if not opt_indices:
        return []

    split_points = [x[0] for x in opt_indices] + [len(chunk_elements)]
    for i, (start_idx, label) in enumerate(opt_indices):
        end_idx = split_points[i + 1]
        opt_elems = [blk._element for _, blk in chunk_elements[start_idx:end_idx]]
        # (Simplified marking check for TF - usually not shuffled but good to have)
        is_marked = False
        options.append(OptionBlock(label, opt_elems, is_marked))
        
    return options

def _fallback_inline_options(chunk_elements: List[Tuple[str, object]]) -> Tuple[List[OxmlElement], List[OptionBlock]]:
    """Try to find inline options (Câu 1: ... A. ... B. ...)"""
    stems = []
    options = []
    temp_options = []
    
    for kind, block in chunk_elements:
        if kind == 'p':
            inline_ops = _split_inline_options_smart(block)
            if inline_ops:
                for op in inline_ops:
                    temp_options.append(OptionBlock(op["label"], [op["element"]], op["is_marked"]))
            else:
                if not temp_options: stems.append(block._element)
        else:
            if not temp_options: stems.append(block._element)
            
    if temp_options:
        return stems, temp_options
    return [], []

def _parse_options(chunk_elements: List[Tuple[str, object]]) -> Tuple[str, List[OxmlElement], List[OptionBlock]]:
    """Master function to determine mode and parse options"""
    # 1. Try MCQ Block-based
    mcq_options = _parse_mcq_options(chunk_elements)
    if mcq_options:
        first_opt_lbl = mcq_options[0].label
        first_opt_idx = -1
        for idx, (kind, block) in enumerate(chunk_elements):
             if kind == 'p':
                 text = _get_text(block).strip()
                 m = OPTION_START_PATTERN.match(text)
                 if m and m.group(1).upper() == first_opt_lbl:
                     first_opt_idx = idx
                     break
        
        if first_opt_idx != -1:
            stems = [blk._element for _, blk in chunk_elements[:first_opt_idx]]
            return "mcq", stems, mcq_options

    # 2. Try True/False Block-based
    tf_options = _parse_tf_options(chunk_elements)
    if tf_options:
        first_opt_lbl = tf_options[0].label
        first_opt_idx = -1
        for idx, (kind, block) in enumerate(chunk_elements):
             if kind == 'p':
                 text = _get_text(block).strip()
                 m = SUB_OPTION_PATTERN.match(text)
                 if m and m.group(1).lower() == first_opt_lbl:
                     first_opt_idx = idx
                     break
        if first_opt_idx != -1:
            stems = [blk._element for _, blk in chunk_elements[:first_opt_idx]]
            return "true_false", stems, tf_options

    # 3. Try Inline Fallback
    stems_inline, ops_inline = _fallback_inline_options(chunk_elements)
    if ops_inline:
         if len(ops_inline) >= 2:
             return "mcq", stems_inline, ops_inline

    # 4. Explicit Short Answer (No options but valid question)
    return "short", [blk._element for _, blk in chunk_elements], []


def _parse_questions_in_range(blocks: List[Tuple[str, object]]) -> List[QuestionBlock]:
    if not blocks: return []
    q_indices = []
    for idx, (kind, block) in enumerate(blocks):
        if QUESTION_PATTERN.match(_get_text(block)): q_indices.append(idx)
    if not q_indices: return []
    questions = []
    for i, start in enumerate(q_indices):
        next_q_start = q_indices[i + 1] if i + 1 < len(q_indices) else len(blocks)
        raw_chunk = blocks[start:next_q_start]
        first_text = _get_text(raw_chunk[0][1])
        match = QUESTION_PATTERN.match(first_text)
        q_num = int(match.group(1)) if match else 0
        raw_label = match.group(0) if match else "Câu ?"
        mode, stems, opts = _parse_options(raw_chunk)
        questions.append(QuestionBlock(q_num, raw_label, stems, opts, mode))
    
    return questions


def parse_exam_template(source_bytes: bytes) -> ExamStructure:
    doc = Document(io.BytesIO(source_bytes))
    all_blocks = list(_iter_block_items(doc))

    # 1. Tách phần "ĐÁP ÁN" (để lấy dữ liệu và XÓA khỏi đề thi)
    main_blocks = []
    answer_key_blocks = []

    found_answer_header = False
    for idx, (kind, block) in enumerate(all_blocks):
        text = _get_text(block).strip()
        if ANSWER_HEADER_PATTERN.match(text):
            main_blocks = all_blocks[:idx]
            answer_key_blocks = all_blocks[idx:]
            found_answer_header = True
            break

    if not found_answer_header:
        main_blocks = all_blocks

    # 2. Parse đáp án từ phần bị cắt bỏ
    table_answers = {}
    if answer_key_blocks:
        table_answers = _extract_answers_from_blocks(answer_key_blocks)

    # 3. Xử lý Footer và bảng đáp án "lọt lưới" (nếu không có header ĐÁP ÁN)
    structure = ExamStructure()
    footer_start_idx = len(main_blocks)

    # Tìm footer marker ("HẾT")
    for idx, (kind, block) in enumerate(main_blocks):
        if END_NOTE_PATTERN.search(_get_text(block)):
            footer_start_idx = idx
            break

    content_blocks = main_blocks[:footer_start_idx]
    raw_footer_blocks = main_blocks[footer_start_idx:]

    # Lọc Footer: Nếu không tìm thấy header ĐÁP ÁN, quét footer tìm bảng đáp án để xóa
    clean_footer_elements = []
    footer_answers = {}

    if not found_answer_header:
        # Scan footer blocks for tables that look like answer keys
        temp_footer_answ_blocks = []
        for kind, block in raw_footer_blocks:
            if kind == 'tbl':
                # Thử extract từ bảng này
                mini_map = _extract_answers_from_blocks([(kind, block)])
                if len(mini_map) >= 5:  # Ngưỡng tin cậy: bảng có >5 đáp án
                    footer_answers.update(mini_map)
                    # KHÔNG thêm vào clean_footer -> XÓA
                    continue
            clean_footer_elements.append(block._element)
        table_answers.update(footer_answers)
    else:
        clean_footer_elements = [blk._element for _, blk in raw_footer_blocks]

    structure.footer_elements = clean_footer_elements

    # 4. Chia Section (Phần I, Phần II...)
    section_starts = []
    for idx, (_, block) in enumerate(content_blocks):
        if SECTION_PATTERN.match(_get_text(block)): section_starts.append(idx)

    if not section_starts:
        first_q_idx = 0
        for idx, (_, block) in enumerate(content_blocks):
            if QUESTION_PATTERN.match(_get_text(block)):
                first_q_idx = idx
                break
        structure.header_elements = [blk._element for _, blk in content_blocks[:first_q_idx]]
        qs = _parse_questions_in_range(content_blocks[first_q_idx:])
        structure.sections.append(Section("", [], qs))
    else:
        structure.header_elements = [blk._element for _, blk in content_blocks[:section_starts[0]]]
        for i, start_idx in enumerate(section_starts):
            end_idx = section_starts[i + 1] if i + 1 < len(section_starts) else len(content_blocks)
            sec_blocks = content_blocks[start_idx:end_idx]

            # Lấy title chính xác
            title_block = sec_blocks[0][1]
            title_text = _get_text(title_block)

            q_start = len(sec_blocks)
            for j, (_, blk) in enumerate(sec_blocks):
                if j == 0: continue
                if QUESTION_PATTERN.match(_get_text(blk)):
                    q_start = j
                    break
            info = [blk._element for _, blk in sec_blocks[1:q_start]]
            qs = _parse_questions_in_range(sec_blocks[q_start:])
            structure.sections.append(Section(title_text, info, qs))

    # 5. Validate Validation
    total_questions = sum(len(sec.questions) for sec in structure.sections)
    if total_questions == 0:
        raise EmptyQuestionError("Không tìm thấy bất kỳ câu hỏi nào (bắt đầu bằng 'Câu', 'Bài').")

    # 6. Merge đáp án từ bảng vào câu hỏi
    if table_answers:
        for sec in structure.sections:
            for q in sec.questions:
                if q.original_idx in table_answers:
                    correct_char = table_answers[q.original_idx]
                    for opt in q.options:
                        if opt.label.upper().startswith(correct_char):
                            opt.is_correct = True
                        else:
                            opt.is_correct = False
    
    if not table_answers and not footer_answers:
         # Check if any question has answers marked inline (underline/red)
         has_inline_answers = False
         for sec in structure.sections:
             for q in sec.questions:
                 for opt in q.options:
                     if opt.is_correct:
                         has_inline_answers = True
                         break
                 if has_inline_answers: break
             if has_inline_answers: break
         
         if not has_inline_answers and not found_answer_header:
             raise AnswerKeyNotFoundError("Không tìm thấy bảng đáp án (Header 'ĐÁP ÁN') và không có đáp án gạch chân/tô đỏ.")

    return structure
