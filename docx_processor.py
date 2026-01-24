# import os
# import zipfile
# import openpyxl
# import logging
# import io
# from typing import Dict, List
# from core_logic import parse_exam_template, generate_variant_from_structure
#
# logger = logging.getLogger("worker")
#
#
# def process_exam_batch(source_bytes: bytes, job_id: str, num_variants: int, output_zip_path: str) -> None:
#     """
#     Xử lý tạo nhiều đề thi và ghi trực tiếp vào file ZIP trên đĩa để tiết kiệm RAM.
#
#     Args:
#         source_bytes: Nội dung file DOCX gốc.
#         job_id: ID của job hiện tại.
#         num_variants: Số lượng đề cần tạo.
#         output_zip_path: Đường dẫn tuyệt đối để lưu file ZIP kết quả.
#     """
#     # 1. Parse cấu trúc đề thi một lần duy nhất (CPU intensive)
#     logger.info(f"[{job_id}] Parsing template structure...")
#     structure = parse_exam_template(source_bytes)
#
#     all_answers_data = {}
#
#     # 2. Mở ZipFile ở chế độ write trực tiếp lên đĩa (Disk I/O)
#     # compression=zipfile.ZIP_DEFLATED giúp giảm dung lượng file đầu ra
#     with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
#         logger.info(f"[{job_id}] Generating {num_variants} variants directly to disk...")
#
#         for i in range(num_variants):
#             exam_code = str(101 + i)
#             # Tạo seed ổn định: hash(job_id + code) đảm bảo nếu chạy lại job này sẽ ra kết quả y hệt
#             current_seed = hash(f"{job_id}_{exam_code}")
#
#             # Generate nội dung DOCX (vẫn tốn RAM tạm thời cho 1 file này)
#             docx_bytes, answers_list = generate_variant_from_structure(
#                 source_bytes=source_bytes,
#                 structure=structure,
#                 seed=current_seed,
#                 exam_code=exam_code
#             )
#
#             # Lưu đáp án
#             all_answers_data[exam_code] = answers_list
#
#             # Ghi bytes vào zip ngay lập tức
#             zf.writestr(f"Ma_De_{exam_code}.docx", docx_bytes)
#
#             # QUAN TRỌNG: Giải phóng bộ nhớ của biến docx_bytes ngay lập tức
#             # Python GC sẽ thu hồi vùng nhớ này cho vòng lặp tiếp theo
#             del docx_bytes
#
#             # 3. Tạo file Excel đáp án (File này thường nhẹ, giữ trong RAM ok)
#         logger.info(f"[{job_id}] Generating Excel answer key...")
#         excel_bytes = _generate_excel_answers(all_answers_data, job_id)
#         zf.writestr(f"Bang_Dap_An_Tong_Hop_{job_id}.xlsx", excel_bytes)
#
#     # Log kích thước file cuối cùng để monitoring
#     file_size_mb = os.path.getsize(output_zip_path) / (1024 * 1024)
#     logger.info(f"[{job_id}] Completed. Output size: {file_size_mb:.2f} MB")
import os
import zipfile
import openpyxl
import logging
import io
import time
from typing import Callable, Optional
from core_logic import parse_exam_template, generate_variant_from_structure

logger = logging.getLogger("worker")


def process_exam_batch(
        source_bytes: bytes,
        job_id: str,
        num_variants: int,
        output_zip_path: str,
        progress_callback: Optional[Callable[[], None]] = None  # <--- NEW: Nhận hàm callback
) -> None:
    logger.info(f"[{job_id}] Parsing template structure...")
    structure = parse_exam_template(source_bytes)

    all_answers_data = {}
    last_heartbeat_time = time.time()
    HEARTBEAT_INTERVAL = 30  # Giây (nên nhỏ hơn VisibilityTimeout của SQS)

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        logger.info(f"[{job_id}] Generating {num_variants} variants...")

        for i in range(num_variants):
            # 1. Logic xử lý chính
            exam_code = str(101 + i)
            current_seed = hash(f"{job_id}_{exam_code}")

            docx_bytes, answers_list = generate_variant_from_structure(
                source_bytes=source_bytes,
                structure=structure,
                seed=current_seed,
                exam_code=exam_code
            )

            all_answers_data[exam_code] = answers_list
            zf.writestr(f"Ma_De_{exam_code}.docx", docx_bytes)
            del docx_bytes

            # 2. ACTIVE HEARTBEAT CHECK
            # Kiểm tra xem đã đến lúc cần gia hạn SQS chưa
            if progress_callback and (time.time() - last_heartbeat_time > HEARTBEAT_INTERVAL):
                try:
                    logger.info(f"[{job_id}] Sending heartbeat signal from processor...")
                    progress_callback()  # Gọi ngược về worker để gia hạn
                    last_heartbeat_time = time.time()  # Reset đồng hồ
                except Exception as e:
                    # Không để lỗi network làm chết job đang chạy tốt
                    logger.warning(f"[{job_id}] Heartbeat callback failed: {e}")

        # Tạo Excel
        excel_bytes = _generate_excel_answers(all_answers_data, job_id)
        zf.writestr(f"Bang_Dap_An_{job_id}.xlsx", excel_bytes)

    file_size_mb = os.path.getsize(output_zip_path) / (1024 * 1024)
    logger.info(f"[{job_id}] Completed. Output size: {file_size_mb:.2f} MB")


# ... (Hàm _generate_excel_answers giữ nguyên)

def _generate_excel_answers(all_answers_data: dict, job_id: str) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dap An Chi Tiet"

    sorted_codes = sorted(all_answers_data.keys())
    headers = ["Câu"] + [f"Mã {code}" for code in sorted_codes]
    ws.append(headers)

    max_questions = 0
    if sorted_codes:
        max_questions = len(all_answers_data[sorted_codes[0]])

    for q_idx in range(max_questions):
        row_data = [q_idx + 1]
        for code in sorted_codes:
            ans_list = all_answers_data[code]
            ans = ans_list[q_idx] if q_idx < len(ans_list) else ""
            row_data.append(ans)
        ws.append(row_data)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()