"""
Answer Parser Service — extracts answer maps from raw text and parsed exam structures.
Handles MCQ, True/False, and Short Answer question types.
"""
import re
import logging

logger = logging.getLogger("server.answer_parser")


def parse_answer_map_from_text(raw_text: str) -> dict[str, str]:
    """
    Parse raw editor text to extract an answer map.
    
    Supports:
    - MCQ answers: lines starting with *A. or *A)
    - True/False answers: lowercase *a. or *a) (accumulates multiple)
    - Short answers: "Đáp án: ..." lines
    - ID-based mapping: [ID:hex] tags take priority over index-based

    Returns:
        dict mapping question ID (hash) or index (str) to answer string.
    """
    answer_map: dict[str, str] = {}
    current_id: str | None = None
    current_q_idx = 0

    # Regex patterns
    id_pattern = re.compile(r"\[ID:([a-fA-F0-9]{8,})\]")
    q_idx_pattern = re.compile(r"^\s*(?:Câu|Bai|Bài)\s+(\d+)", re.IGNORECASE)
    ans_pattern = re.compile(r"^\s*\*\s*([A-Za-z])[\.)]", re.IGNORECASE)
    short_ans_pattern = re.compile(
        r"^\s*(?:Đáp án|ĐÁP ÁN|Dap an)[:\.]?\s*(.+)", re.IGNORECASE
    )

    for line in raw_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Check for ID Tag
        id_match = id_pattern.search(line)
        if id_match:
            current_id = id_match.group(1)

        # Check for Question Number (fallback context)
        q_match = q_idx_pattern.match(line)
        if q_match:
            current_q_idx = int(q_match.group(1))
            if not id_match:
                current_id = None

        # Check for Marked Answer (MCQ/TF: *A. or *a))
        if line.startswith('*'):
            ans_match = ans_pattern.match(line)
            if ans_match:
                ans_char_raw = ans_match.group(1)
                ans_char = ans_char_raw.upper()
                is_true_false = ans_char_raw.islower()

                # PRIORITY 1: Map by ID (Hash)
                if current_id:
                    if is_true_false and current_id in answer_map:
                        existing = answer_map[current_id]
                        if ans_char not in existing.split(','):
                            answer_map[current_id] = f"{existing},{ans_char}"
                    else:
                        answer_map[current_id] = ans_char

                # PRIORITY 2: Map by Index (Legacy/Fallback)
                elif current_q_idx > 0:
                    key = str(current_q_idx)
                    if is_true_false and key in answer_map:
                        existing = answer_map[key]
                        if ans_char not in existing.split(','):
                            answer_map[key] = f"{existing},{ans_char}"
                    else:
                        answer_map[key] = ans_char

        # Check for Short Answer: "Đáp án: 123"
        short_match = short_ans_pattern.match(line)
        if short_match:
            ans_text = short_match.group(1).strip()
            if ans_text:
                if current_id:
                    answer_map[current_id] = ans_text
                    logger.debug(f"Short Answer Mapped ID {current_id} -> {ans_text}")
                elif current_q_idx > 0:
                    answer_map[str(current_q_idx)] = ans_text
                    logger.debug(
                        f"Short Answer Mapped Index {current_q_idx} -> {ans_text}"
                    )

    return answer_map


def extract_answers_from_structure(structure) -> dict[int, str]:
    """
    Extract answer map from a parsed ExamStructure.
    Uses global sequential question numbering.

    Returns:
        dict mapping global question index (int) to answer string.
    """
    answer_map: dict[int, str] = {}
    global_q_idx = 0

    for sec in structure.sections:
        for q in sec.questions:
            global_q_idx += 1

            # Find correct option labels
            corrects = [opt.label for opt in q.options if opt.is_correct]
            if corrects:
                if q.mode == 'true_false':
                    # TF: Store all correct labels (comma-separated)
                    answer_map[global_q_idx] = ','.join(corrects)
                else:
                    # MCQ: Store first correct label
                    answer_map[global_q_idx] = corrects[0]
            elif q.correct_answer_text and q.mode == 'short':
                # Short Answer: Store the answer text
                answer_map[global_q_idx] = q.correct_answer_text

    return answer_map
