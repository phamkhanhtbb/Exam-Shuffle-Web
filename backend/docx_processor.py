"""
DOCX Processor — Orchestrates the Batch Generation of Exam Variants.
This module takes a template DOCX, parses its structure, and uses multiple
threads to generate several shuffled variants in parallel.
"""

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

# -- Performance Configuration --
# We use a ThreadPoolExecutor because the XML parsing/serialization in python-docx
# (via lxml) releases the Global Interpreter Lock (GIL), allowing for actual parallelism.
MAX_WORKERS = 8


def _generate_single_variant(args):
    """
    Helper function designated for the thread pool to generate a single variant.
    Args:
        args: A tuple containing (source_bytes, structure, job_id, exam_code, external_answer_map)
    Returns:
        A tuple of (exam_code, docx_bytes, answers_list)
    """
    source_bytes, structure, job_id, exam_code, external_answer_map = args

    # Generate a deterministic seed based on Job ID and Exam Code
    # to ensure consistency if the same variant is regenerated.
    current_seed = hash(f"{job_id}_{exam_code}")

    # Delegate the heavy lifting of shuffling and serializing to the core logic.
    docx_bytes, answers_list = generate_variant_from_structure(
        source_bytes=source_bytes,
        structure=structure,
        seed=current_seed,
        exam_code=exam_code,
        external_answer_map=external_answer_map,
    )

    return exam_code, docx_bytes, answers_list


def process_exam_batch(
    source_bytes: bytes,
    job_id: str,
    num_variants: int,
    output_zip_path: str,
    progress_callback: Optional[Callable[[int], None]] = None,
    external_answer_map: Optional[dict] = None,
    exam_codes_str: Optional[str] = None,
) -> None:
    """
    Main entry point for processing a batch of exams.
    1. Parses the template structure.
    2. Determines the naming scheme (exam codes).
    3. Runs variant generation in parallel.
    4. Bundles everything into a ZIP file.
    5. Generates an Excel file for the answer keys.
    """
    logger.info(f"[{job_id}] Parsing template structure...")
    doc = Document(io.BytesIO(source_bytes))

    # Step 1: Identify questions, options, and parts in the original document.
    structure = parse_exam_template(source_bytes, doc)

    all_answers_data = {}

    # Step 2: Parse custom exam codes (e.g., "101,102,103" or "201" for a sequence).
    custom_codes = []
    if exam_codes_str and exam_codes_str.strip():
        parts = [c.strip() for c in exam_codes_str.split(",") if c.strip()]
        if len(parts) == 1 and parts[0].isdigit():
            # If a single number like "201" is given, auto-generate 201, 202, ...
            start_code = int(parts[0])
            custom_codes = [str(start_code + i) for i in range(num_variants)]
        else:
            custom_codes = parts

    # Step 3: Prepare arguments for the thread pool.
    variant_args = []
    for i in range(num_variants):
        if i < len(custom_codes):
            exam_code = custom_codes[i]
        else:
            exam_code = str(101 + i)  # Default starting code is 101.
        variant_args.append(
            (source_bytes, structure, job_id, exam_code, external_answer_map)
        )

    t_start = time.perf_counter()

    # Step 4: Open a ZIP file to store all generated variants.
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        logger.info(
            f"[{job_id}] Generating {num_variants} variants with {MAX_WORKERS} threads..."
        )

        # Use ThreadPoolExecutor for parallel generation.
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all generation tasks.
            future_to_code = {
                executor.submit(_generate_single_variant, args): args[
                    3
                ]  # args[3] = exam_code
                for args in variant_args
            }

            completed = 0
            HEARTBEAT_INTERVAL = 1.0  # seconds
            last_heartbeat_time = time.time()
            for future in as_completed(future_to_code):
                exam_code = future_to_code[future]
                try:
                    # Get results from the thread.
                    exam_code, docx_bytes, answers_list = future.result()

                    # Store data for the master answer key.
                    all_answers_data[exam_code] = answers_list

                    # Add the generated file to the ZIP.
                    zf.writestr(f"Ma_De_{exam_code}.docx", docx_bytes)
                    del docx_bytes

                    completed += 1
                    
                    if progress_callback:
                        progress_pct = int((completed / num_variants) * 100)
                        progress_callback(progress_pct)

                    # Periodic logging of progress.
                    if completed % 10 == 0:
                        elapsed = time.perf_counter() - t_start
                        rate = completed / elapsed
                        remaining = (num_variants - completed) / rate if rate > 0 else 0
                        logger.info(
                            f"[{job_id}] Progress: {completed}/{num_variants} "
                            f"({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)"
                        )

                except Exception as e:
                    logger.error(
                        f"[{job_id}] Error generating variant {exam_code}: {e}"
                    )
                    raise

                # Step 5: Active Heartbeat Check.
                # We periodically call the progress_callback to tell SQS/Worker
                # that we are still alive and working, preventing the job from being retried.
                if progress_callback and (
                    time.time() - last_heartbeat_time > HEARTBEAT_INTERVAL
                ):
                    try:
                        logger.info(
                            f"[{job_id}] Sending heartbeat signal from processor..."
                        )
                        progress_callback()
                        last_heartbeat_time = time.time()
                    except Exception as e:
                        logger.warning(f"[{job_id}] Heartbeat callback failed: {e}")

        # Step 6: Generate the master Answer Key Excel file.
        excel_bytes = _generate_excel_answers(all_answers_data, job_id)
        zf.writestr(f"Bang_Dap_An_{job_id}.xlsx", excel_bytes)

    t_total = time.perf_counter() - t_start
    file_size_mb = os.path.getsize(output_zip_path) / (1024 * 1024)
    logger.info(
        f"[{job_id}] Completed in {t_total:.1f}s. Output size: {file_size_mb:.2f} MB. "
        f"Rate: {num_variants / t_total:.1f} variants/sec"
    )


def _generate_excel_answers(all_answers_data: dict, job_id: str) -> bytes:
    """
    Creates an Excel spreadsheet containing the answer keys for all generated variants.
    Columns: Question Number, Code 101, Code 102, ...
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Detailed Answer Key"

    sorted_codes = sorted(all_answers_data.keys())
    # Excel header row.
    headers = ["Question"] + [f"Code {code}" for code in sorted_codes]
    ws.append(headers)

    # Find the maximum number of questions among all variants.
    max_questions = 0
    if sorted_codes:
        max_questions = max(len(all_answers_data[k]) for k in sorted_codes)

    # Populate the rows.
    for q_idx in range(max_questions):
        row_data = [q_idx + 1]
        for code in sorted_codes:
            ans_list = all_answers_data[code]
            ans = ans_list[q_idx] if q_idx < len(ans_list) else ""

            # Heuristic: Try to convert string answers to numbers (integers or floats)
            # for nicer formatting in Excel (especially for numeric Part 3 answers).
            if isinstance(ans, str) and ans.strip():
                clean_ans = ans.strip()
                # Check if it looks like a single number (integer or decimal).
                if re.match(r"^[-+]?[0-9]+[.,]?[0-9]*$", clean_ans):
                    try:
                        # Normalize decimal separator (comma to dot).
                        val_str = clean_ans.replace(",", ".")
                        val_float = float(val_str)
                        # Store as integer if it has no fractional part.
                        if val_float.is_integer():
                            ans = int(val_float)
                        else:
                            ans = val_float
                    except ValueError:
                        pass

            row_data.append(ans)
        ws.append(row_data)

    # Return the Workbook as bytes.
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
