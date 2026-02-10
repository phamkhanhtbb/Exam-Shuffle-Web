import os
import re
import zipfile
import openpyxl
import logging
import io
import time
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from docx import Document
from core import parse_exam_template, generate_variant_from_structure

logger = logging.getLogger("worker")

# Use 8 threads (half of 16 cores) to leave headroom for other work
# lxml (used by python-docx) releases GIL during XML parsing/serialization,
# so threads can provide real parallelism for I/O-bound parts
MAX_WORKERS = 8


def _generate_single_variant(args):
    """Generate a single variant - helper function for thread pool."""
    source_bytes, structure, job_id, exam_code, external_answer_map = args
    current_seed = hash(f"{job_id}_{exam_code}")
    
    docx_bytes, answers_list = generate_variant_from_structure(
        source_bytes=source_bytes,
        structure=structure,
        seed=current_seed,
        exam_code=exam_code,
        external_answer_map=external_answer_map
    )
    
    return exam_code, docx_bytes, answers_list


def process_exam_batch(
        source_bytes: bytes,
        job_id: str,
        num_variants: int,
        output_zip_path: str,

        progress_callback: Optional[Callable[[], None]] = None,
        external_answer_map: Optional[dict] = None
) -> None:
    logger.info(f"[{job_id}] Parsing template structure...")
    doc = Document(io.BytesIO(source_bytes))
    structure = parse_exam_template(source_bytes, doc)

    all_answers_data = {}
    last_heartbeat_time = time.time()
    HEARTBEAT_INTERVAL = 30  # Giây (nên nhỏ hơn VisibilityTimeout của SQS)
    
    # Prepare arguments for all variants
    variant_args = []
    for i in range(num_variants):
        exam_code = str(101 + i)
        variant_args.append((source_bytes, structure, job_id, exam_code, external_answer_map))
    
    t_start = time.perf_counter()
    
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        logger.info(f"[{job_id}] Generating {num_variants} variants with {MAX_WORKERS} threads...")
        
        # Use ThreadPoolExecutor for parallel generation
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_code = {
                executor.submit(_generate_single_variant, args): args[3]  # args[3] = exam_code
                for args in variant_args
            }
            
            completed = 0
            for future in as_completed(future_to_code):
                exam_code = future_to_code[future]
                try:
                    exam_code, docx_bytes, answers_list = future.result()
                    
                    all_answers_data[exam_code] = answers_list
                    zf.writestr(f"Ma_De_{exam_code}.docx", docx_bytes)
                    del docx_bytes
                    
                    completed += 1
                    
                    # Log progress every 10 variants
                    if completed % 10 == 0:
                        elapsed = time.perf_counter() - t_start
                        rate = completed / elapsed
                        remaining = (num_variants - completed) / rate if rate > 0 else 0
                        logger.info(f"[{job_id}] Progress: {completed}/{num_variants} "
                                    f"({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)")
                    
                except Exception as e:
                    logger.error(f"[{job_id}] Error generating variant {exam_code}: {e}")
                    raise
                
                # ACTIVE HEARTBEAT CHECK
                if progress_callback and (time.time() - last_heartbeat_time > HEARTBEAT_INTERVAL):
                    try:
                        logger.info(f"[{job_id}] Sending heartbeat signal from processor...")
                        progress_callback()
                        last_heartbeat_time = time.time()
                    except Exception as e:
                        logger.warning(f"[{job_id}] Heartbeat callback failed: {e}")

        # Tạo Excel
        excel_bytes = _generate_excel_answers(all_answers_data, job_id)
        zf.writestr(f"Bang_Dap_An_{job_id}.xlsx", excel_bytes)
    
    t_total = time.perf_counter() - t_start
    file_size_mb = os.path.getsize(output_zip_path) / (1024 * 1024)
    logger.info(f"[{job_id}] Completed in {t_total:.1f}s. Output size: {file_size_mb:.2f} MB. "
                f"Rate: {num_variants/t_total:.1f} variants/sec")


def _generate_excel_answers(all_answers_data: dict, job_id: str) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dap An Chi Tiet"

    sorted_codes = sorted(all_answers_data.keys())
    headers = ["Câu"] + [f"Mã {code}" for code in sorted_codes]
    ws.append(headers)

    max_questions = 0
    if sorted_codes:
        max_questions = max(len(all_answers_data[k]) for k in sorted_codes)

    for q_idx in range(max_questions):
        row_data = [q_idx + 1]
        for code in sorted_codes:
            ans_list = all_answers_data[code]
            ans = ans_list[q_idx] if q_idx < len(ans_list) else ""
            
            # Try to convert to number if possible (Part 3 requirement)
            if isinstance(ans, str) and ans.strip():
                clean_ans = ans.strip()
                # Replace Vietnamese/European decimal comma with dot for parsing
                # But be careful not to break "1,2" (list) vs "1,2" (decimal)
                # Heuristic: If it looks like a SINGLE number
                if re.match(r'^[-+]?[0-9]+[.,]?[0-9]*$', clean_ans):
                    try:
                        # Normalize decimal separator
                        val_str = clean_ans.replace(',', '.')
                        val_float = float(val_str)
                        # Check if integer
                        if val_float.is_integer():
                            ans = int(val_float)
                        else:
                            ans = val_float
                    except ValueError:
                        pass
            
            row_data.append(ans)
        ws.append(row_data)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()