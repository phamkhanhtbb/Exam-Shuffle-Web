
import re

# --- CONFIG & REGEX PATTERNS ---
# Cập nhật Regex để bắt được cả "PHẦN I" và "I. TÊN PHẦN"
SECTION_PATTERN = re.compile(r"^\s*(?:PH[ẦA]N\s+[IVX0-9]+|[IVX]+\.\s+)(.*)", re.IGNORECASE)
QUESTION_PATTERN = re.compile(r"^\s*(?:Câu|Bai|Bài)\s+(\d+)", re.IGNORECASE)
OPTION_START_PATTERN = re.compile(r"^\s*([ABCD])\s*[\.|\)]\s*")
INLINE_OPTION_PATTERN = re.compile(r"(?:^|\s+)([ABCD])[\.\)]")
SUB_OPTION_PATTERN = re.compile(r"^\s*([a-d])\s*[\)|\.]\s*")
END_NOTE_PATTERN = re.compile(r"^\s*[-]*\s*(HẾT|GIÁM THỊ|GHI CHÚ)\s*[-]*", re.IGNORECASE)
# Regex nhận diện tiêu đề phần đáp án để cắt bỏ
ANSWER_HEADER_PATTERN = re.compile(r"^\s*ĐÁP\s*ÁN.*$", re.IGNORECASE)
