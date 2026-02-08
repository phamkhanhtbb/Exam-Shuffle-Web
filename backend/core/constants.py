
import re

# --- CONFIG & REGEX PATTERNS ---
# Cập nhật Regex để bắt được cả "PHẦN I", "PHẦN 1", "I.", "PHẦN TRẮC NGHIỆM"
SECTION_PATTERN = re.compile(r"^\s*(?:PH[ẦA]N\s+(?:[IVX]+|\d+|TRẮC\s+NGHIỆM|TỰ\s+LUẬN)|[IVX]+\.)[\s\.:]*(.*)$", re.IGNORECASE)
# Fixed: Allow optional [ID:xxx] prefix before Câu
QUESTION_PATTERN = re.compile(r"^\s*(?:\[ID:[^\]]*\]\s*)?(?:Câu|Bai|Bài)\s+(\d+)", re.IGNORECASE)
# Capturing group 1: Asterisk (*), Group 2: Letter
# Fixed: Remove \s* between asterisk and letter to match *A. format directly
OPTION_START_PATTERN = re.compile(r"^\s*(\*?)([A-H])\s*[\.\)]\s*")
# Improved: Capture asterisk before OR after the letter (for *A. and A.* formats)
# Group 1: Asterisk before, Group 2: Letter, Group 3: Asterisk after
# FIX: Only exclude digits before space (e.g., "2,5 A."), allow dots/commas (e.g., "đặc. B.")
INLINE_OPTION_PATTERN = re.compile(r"(?:^|(?<![0-9])\s)(\*?)([A-H])[\.\)](\*?)")
# Fix: Limit sub-options to a-d (standard) and ONLY ')' as requested.
SUB_OPTION_PATTERN = re.compile(r"^\s*(\*?)([a-d])\s*\)\s*")
END_NOTE_PATTERN = re.compile(r"^\s*[-]*\s*(HẾT|GIÁM THỊ|GHI CHÚ)\s*[-]*", re.IGNORECASE)
# Regex nhận diện tiêu đề phần đáp án để cắt bỏ (tránh match 'Đáp án: ...' của câu hỏi)
ANSWER_HEADER_PATTERN = re.compile(r"^\s*(?:BẢNG\s*)?ĐÁP\s*ÁN\s*(?:CHI TIẾT|TRẮC NGHIỆM|THAM KHẢO|PHẦN\s+.*)?\s*$", re.IGNORECASE)
