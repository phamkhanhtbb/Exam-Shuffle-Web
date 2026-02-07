import io
import re
import hashlib
from typing import List, Tuple, Dict, Optional
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

def _generate_content_hash(text: str) -> str:
    """Generate a short hash from question content for matching."""
    # Normalize: lowercase, collapse whitespace, take first 200 chars
    clean = re.sub(r'\s+', ' ', text).strip().lower()[:200]
    return hashlib.md5(clean.encode('utf-8')).hexdigest()[:12]


def _split_inline_options_smart(paragraph) -> Tuple[Optional[OxmlElement], List[dict]]:
    full_text, mask = _build_paragraph_mask(paragraph)
    matches = list(INLINE_OPTION_PATTERN.finditer(full_text))
    
    if not matches: return None, []
    
    pre_element = None
    # Check for content BEFORE the first option
    first_start = matches[0].start()
    if first_start > 0:
        # Check if it's just whitespace?
        # Even if it's whitespace, usually we might want to keep it or ignore it.
        # But if it contains text (like "d. ..."), we MUST keep it.
        if full_text[:first_start].strip():
             pre_element = _slice_paragraph_runs(paragraph, 0, first_start)

    results = []
    
    for i, match in enumerate(matches):
        # Group 1: Asterisk before, Group 2: Letter, Group 3: Asterisk after
        asterisk_before = match.group(1)
        label = match.group(2).upper()
        asterisk_after = match.group(3) if match.lastindex >= 3 else ""
        
        # Start index of the whole match
        start_idx = match.start()
        # End index is start of next match or end of text
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        
        rich_element = _slice_paragraph_runs(paragraph, start_idx, end_idx)
        
        # Determine strict label char location for masking check (red underline)
        # match.start(2) is the index of the Letter
        label_char_idx = match.start(2)
        
        is_marked = False
        # Check 1: Explicit asterisk (before OR after)
        if asterisk_before == '*' or asterisk_after == '*':
            is_marked = True
        # Check 2: Red/Underline mask
        elif label_char_idx < len(mask) and mask[label_char_idx]:
            is_marked = True
        elif any(mask[start_idx:end_idx]):
            is_marked = True
            
        results.append({"label": label, "element": rich_element, "is_marked": is_marked})
    
    return pre_element, results

# Fix import in utils: _slice_paragraph_runs is in utils.
from .utils import _slice_paragraph_runs


def _extract_answers_from_blocks(blocks: List[Tuple[str, object]]) -> Dict[int, str]:
    """Quét đáp án từ một list các block (dùng cho phần ĐÁP ÁN bị cắt ra)"""
    answers_map = {}
    q_pat = re.compile(r"^\s*(?:Câu)?\s*(\d+)[\.:]?\s*$")
    a_pat = re.compile(r"^\s*([A-D])\s*$")

    # Regex for text-based answers: "1. A", "1: A", "1 A", "Câu 1: A"
    # Capture Group 1: Question Num, Group 2: Answer Letter
    text_ans_pat = re.compile(r"(?:Câu|Bài)?\s*(\d+)[\.:\s-]*([A-D])\b", re.IGNORECASE)

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
                if valid_pairs >= 5:
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
        
        elif kind == 'p':
            # Chiến thuật 3: Text base (Paragraph)
            # Scan for all matches in the paragraph text
            text = _get_text(block).strip()
            matches = text_ans_pat.findall(text)
            if matches:
                 # logger.debug(f"Found matches in text: {matches[:5]}...")
                 for q_str, a_str in matches:
                    try:
                        q_num = int(q_str)
                        # Avoid overwriting if already found? Or Overwrite?
                        # Usually last wins or first wins. Let's update.
                        answers_map[q_num] = a_str.upper()
                    except:
                        pass
    
    if answers_map:
        pass
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
             # DEBUG LOG
             # try:
             #    if "A." in text or "C." in text:
             #        print(f"[DEBUG] Check Option Line: {repr(text)} -> Match: {bool(match)}")
             # except: pass
             
             if match:
                 # Group 1: *, Group 2: Letter
                 asterisk = match.group(1)
                 letter = match.group(2).upper()
                 
                 # --- FIX: INLINE OPTION DETECTION ---
                 # If this line ALSO contains " B." or " C." etc., it might be an inline option line.
                 # OPTION_START_PATTERN matches start of string.
                 # Check if there are other matches of INLINE_OPTION_PATTERN in the REST of the text
                 # excluding the start match.
                 
                 remaining_text = text[match.end():]
                 if INLINE_OPTION_PATTERN.search(remaining_text):
                      # Detect multiple options in this line -> Skip Block Parser
                      # Let _fallback_inline_options handle it.
                      continue
                 # ------------------------------------
                 
                 try:
                     # logger.debug(f"Found Vertical Option: {letter}")
                     pass
                 except: pass

                 opt_indices.append((idx, letter, asterisk == '*'))
    
    if not opt_indices:
        return []

    # 2. Slice blocks based on indices
    split_points = [x[0] for x in opt_indices] + [len(chunk_elements)]
    for i, (start_idx, label, has_asterisk) in enumerate(opt_indices):
        end_idx = split_points[i + 1]
        opt_elems = [blk._element for _, blk in chunk_elements[start_idx:end_idx]]
        
        # Check marking (red/underline) or asterisk
        is_marked = has_asterisk
        if not is_marked:
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
                 # Group 1: *, Group 2: letter
                 asterisk = match.group(1)
                 letter = match.group(2).lower()
                 opt_indices.append((idx, letter, asterisk == '*'))
                 
    if not opt_indices:
        return []

    split_points = [x[0] for x in opt_indices] + [len(chunk_elements)]
    for i, (start_idx, label, has_asterisk) in enumerate(opt_indices):
        end_idx = split_points[i + 1]
        opt_elems = [blk._element for _, blk in chunk_elements[start_idx:end_idx]]
        
        is_marked = has_asterisk
        # Also check for red/underline mask if needed for TF? Usually explicit text is better.
        # But let's keep consistency if user used color.
        if not is_marked:
             for blk_idx in range(start_idx, end_idx):
                kind, blk = chunk_elements[blk_idx]
                if kind == 'p' and any(_build_paragraph_mask(blk)[1]):
                    is_marked = True
                    break
        
        options.append(OptionBlock(label, opt_elems, is_marked))
        
    return options

def _fallback_inline_options(chunk_elements: List[Tuple[str, object]]) -> Tuple[List[OxmlElement], List[OptionBlock]]:
    """Try to find inline options (Câu 1: ... A. ... B. ...)"""
    stems = []
    options = []
    temp_options = []
    
    for kind, block in chunk_elements:
        if kind == 'p':
            pre_elem, inline_ops = _split_inline_options_smart(block)
            
            if pre_elem:
                stems.append(pre_elem)
                
            if inline_ops:
                for op in inline_ops:
                    temp_options.append(OptionBlock(op["label"], [op["element"]], op["is_marked"]))
            else:
                 # If no inline options, and no pre_elem (meaning no matches), then append whole block
                 # But duplicate check? 
                 # If inline_ops is empty, pre_elem is None.
                 # So we append block._element.
                 if not pre_elem:
                     if not temp_options: stems.append(block._element)
                     # If temp_options has content, and this block has NO options?
                     # Then it's probably part of the last option? Or a new question text?
                     # _fallback_inline_options assumes if options started, subsequent blocks belong to options?
                     # Or stems?
                     # Current logic: "if not temp_options: stems.append" implies that once options start, 
                     # we don't go back to stems. 
                     # BUT wait: if we found options in previous block, and this block has NO options.
                     # It should probably belong to the LAST option.
                     # But `OptionBlock` doesn't easily support multi-block inline?
                     # Actually `OptionBlock` has `elements` list.
                     # So if `temp_options` is not empty, we add to last option!
                     elif temp_options:
                         temp_options[-1].elements.append(block._element)
                         
        else:
            if not temp_options: stems.append(block._element)
            elif temp_options: temp_options[-1].elements.append(block._element)
            
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
                 if m and m.group(2).upper() == first_opt_lbl:
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
                 if m and m.group(2).lower() == first_opt_lbl:
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
        
        # --- Extract correct_answer_text for ALL modes (fallback or primary for Short Answer) ---
        ans_text = None
        # Check "Đáp án: ..." in stems
        idx_to_remove = -1
        for idx, stem in enumerate(stems):
             txt = _get_text(stem)
             # Basic clean tags
             txt_clean = re.sub(r"\[![a-z]:|\]", "", txt).strip()
             # Expanded regex to capture "Lời giải", "Hướng dẫn", "HD", etc.
             m_ans = re.search(r"(?:Đáp án|ĐÁP ÁN|Dap an|Lời giải|Lơi giải|Loi giai|Hướng dẫn|Huong dan|HD)[:\.]?\s*(.*)", txt_clean, re.IGNORECASE)
             if m_ans:
                 ans_text = m_ans.group(1).strip()
                 # Mark for removal if it's the only thing in the paragraph (or mostly)
                 # Determining if we should remove the whole paragraph:
                 # If the match covers most of the text?
                 # Simplifying: If it starts with the pattern, remove the whole paragraph for safety?
                 # Or just strip? Removing element is safer for Docx structure than modifying text inplace often.
                 if len(txt.strip()) < len(m_ans.group(0)) + 20: # Heuristic: Short line containing answer
                     idx_to_remove = idx
                 break
        
        if idx_to_remove != -1:
             stems.pop(idx_to_remove)

        questions.append(QuestionBlock(
            original_idx=q_num,
            raw_label=raw_label,
            stem_elements=stems,
            options=opts,
            mode=mode,  # FIX: Apply the detected mode (mcq, true_false, short)
            correct_answer_text=ans_text
        ))
        
        # --- Generate Content Hash for reliable matching ---
        stem_text_parts = []
        for el in stems:
            txt = _get_text(el)
            if txt:
                stem_text_parts.append(txt)
        stem_text = " ".join(stem_text_parts) if stem_text_parts else first_text
        questions[-1].content_hash = _generate_content_hash(stem_text)

        # --- IMPROVEMENT: Check last option for "Đáp án: ..." if not found in stem ---
        # "Đáp án: A" often appears at the very end, which _parse_options assigns to the last option.
        if not questions[-1].correct_answer_text and questions[-1].options:
            last_opt = questions[-1].options[-1]
            idx_to_remove_opt = -1
            
            for idx, el in enumerate(last_opt.elements):
                txt = _get_text(el) 
                m_ans = re.search(r"(?:Đáp án|ĐÁP ÁN|Dap an|Lời giải|Lơi giải|Loi giai|Hướng dẫn|Huong dan|HD)[:\.]?\s*(.*)", txt, re.IGNORECASE)
                if m_ans:
                    questions[-1].correct_answer_text = m_ans.group(1).strip()
                    # Remove this element from option
                    idx_to_remove_opt = idx
                    break
            
            if idx_to_remove_opt != -1:
                last_opt.elements.pop(idx_to_remove_opt)


        # --- FIX: Map correct_answer_text to options if not already marked ---
        # This ensures that if the user provided "Đáp án: A", we treat Option A as correct
        # so that generators.py can shuffle it correctly (instead of falling back to static "A").
        q_obj = questions[-1]
        has_marked = any(opt.is_correct for opt in q_obj.options)
        
        if not has_marked and q_obj.correct_answer_text:
            # Clean text (remove special chars) to find "A", "B", "True", "False"
            clean_ans = re.sub(r"[^a-zA-Z]", "", q_obj.correct_answer_text).strip().upper()
            
            # Map for MCQ/TF
            target_lbl = clean_ans
            
            for opt in q_obj.options:
                # Compare label (A, B...) or clean label
                opt_lbl_clean = re.sub(r"[^a-zA-Z]", "", opt.label).strip().upper()
                if opt_lbl_clean == target_lbl:
                    opt.is_correct = True
                    break
    
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
        # Debug log
        # if "ĐÁP ÁN" in text.upper(): print(f"[DEBUG] Check Header: '{text}' -> Match: {bool(ANSWER_HEADER_PATTERN.match(text))}")
        
        if ANSWER_HEADER_PATTERN.match(text):
            # logger.debug(f"Found Answer Header at index {idx}")
            main_blocks = all_blocks[:idx]
            answer_key_blocks = all_blocks[idx:]
            found_answer_header = True
            break

    if not found_answer_header:
        # print("[DEBUG] No Answer Header found.")
        main_blocks = all_blocks

    # 2. Parse đáp án từ phần bị cắt bỏ
    table_answers = {}
    if answer_key_blocks:
        table_answers = _extract_answers_from_blocks(answer_key_blocks)

    # 3. Xử lý Footer và bảng đáp án "lọt lưới" (nếu không có header ĐÁP ÁN)
    structure = ExamStructure()
    footer_start_idx = len(main_blocks)

    # Tìm footer marker ("HẾT")
    # Tìm footer marker ("HẾT")
    for idx, (kind, block) in enumerate(main_blocks):
        if END_NOTE_PATTERN.search(_get_text(block)):
            # Found "HẾT". Check if next blocks are "Đáp án: ..." belonging to the previous question
            # If so, we delay the footer start.
            is_real_footer = True
            
            # Peek ahead
            peek_idx = idx + 1
            while peek_idx < len(main_blocks):
                peek_block = main_blocks[peek_idx][1]
                peek_text = _get_text(peek_block).strip()
                if not peek_text: 
                    peek_idx += 1
                    continue
                
                # Check if it looks like an answer line
                if re.match(r"^(?:Đáp án|ĐÁP ÁN|Dap an)[:\.]", peek_text, re.IGNORECASE):
                    # It matches! Include this block (and the HẾT block?) in content?
                    # Ideally "HẾT" should be footer, but if we include text AFTER it, "HẾT" must be in content too
                    # or we skip HẾT and add text? NO, order matters.
                    # We just push footer_start_idx forward.
                    is_real_footer = False
                    peek_idx += 1
                    # Keep looking in case multiple lines? or one line?
                    # Usually just one. But let's loop.
                    continue
                else:
                    break
            
            if is_real_footer:
                footer_start_idx = idx
                break
            else:
                 # "HẾT" was followed by answer, so it's NOT the start of the footer YET.
                 # We treat "HẾT" as just content here?
                 # If we assume "HẾT" is always valid footer, we have a dilemma.
                 # But if we push footer_start_idx to peek_idx, then "HẾT" becomes content.
                 # Which is fine, the parser will just treat it as text in the last question.
                 # User can delete it or ignore it.
                 pass

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
             # Check for "Đáp án:" marker in stems (Short Answer)
             has_short_answers = False
             for sec in structure.sections:
                 for q in sec.questions:
                     if q.mode == 'short':
                         for stem in q.stem_elements:
                             txt = _get_text(stem)
                             if "Đáp án:" in txt or "ĐÁP ÁN:" in txt.upper():
                                 has_short_answers = True
                                 break
                     if has_short_answers: break
                 if has_short_answers: break
             
             if not has_short_answers:
                raise AnswerKeyNotFoundError("Không tìm thấy bảng đáp án (Header 'ĐÁP ÁN') và không có đáp án gạch chân/tô đỏ/đánh dấu sao (*).")

    return structure
