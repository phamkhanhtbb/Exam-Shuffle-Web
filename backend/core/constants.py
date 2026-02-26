import re

# --- CONFIG & REGEX PATTERNS ---
# Cập nhật Regex:
# - "PHẦN I/II/III. ..." → Match (cho phép text sau PHẦN + số)
# - "I. Chất truyền tin..." → KHÔNG match (standalone Roman numeral + nội dung dài = nội dung câu hỏi)
# - "I." hoặc "II." (chỉ Roman numeral, không text) → Match
SECTION_PATTERN = re.compile(
    r"^\s*(?:"
    r"PH[ẦA]N\s+(?:[IVX]+|\d+|TRẮC\s+NGHIỆM|TỰ\s+LUẬN)[\s\.:]*.*"  # PHẦN + bất kỳ text nào
    r"|"
    r"[IVX]+\.\s*$"  # Standalone Roman numeral (chỉ match nếu hết dòng)
    r")",
    re.IGNORECASE,
)
# Fixed: Allow optional [ID:xxx] prefix before Câu
QUESTION_PATTERN = re.compile(
    r"^\s*(?:\[ID:[^\]]*\]\s*)?(?:Câu|Bai|Bài)\s+(\d+)", re.IGNORECASE
)
# Capturing group 1: Asterisk (*), Group 2: Letter
# Fixed: Remove \s* between asterisk and letter to match *A. format directly
# Capturing group 1: Optional asterisk BEFORE, Group 2: Letter, Group 3: Optional asterisk AFTER
# This ensures we catch both *A. and A.* formats.
OPTION_START_PATTERN = re.compile(r"^\s*(\*?)([A-H])\s*[\.\)]\s*(\*?)")
# Improved: Capture asterisk before OR after the letter (for *A. and A.* formats)
# Group 1: Asterisk before, Group 2: Letter, Group 3: Asterisk after
# FIX: Allow \uFFFC (Object Replacement Char) as separator for cases like "Equation \uFFFCB."
INLINE_OPTION_PATTERN = re.compile(r"(?:^|(?<![0-9])[\s\uFFFC])(\*?)([A-H])[\.\)](\*?)")
# Fix: Limit sub-options to a-d (standard) and ONLY ')' as requested.
# Group 1: Optional asterisk BEFORE, Group 2: letter, Group 3: Optional asterisk AFTER
SUB_OPTION_PATTERN = re.compile(r"^\s*(\*?)([a-d])\s*\)\s*(\*?)")
INLINE_SUB_OPTION_PATTERN = re.compile(
    r"(?:^|(?<![0-9])[\s\uFFFC])(\*?)([a-d])\)\s*(\*?)"
)
END_NOTE_PATTERN = re.compile(
    r"^\s*[-]*\s*(HẾT|GIÁM THỊ|GHI CHÚ)\s*[-]*", re.IGNORECASE
)
# Regex nhận diện tiêu đề phần đáp án để cắt bỏ (tránh match 'Đáp án: ...' của câu hỏi)
ANSWER_HEADER_PATTERN = re.compile(
    r"^\s*(?:BẢNG\s*)?ĐÁP\s*ÁN\s*(?:CHI TIẾT|TRẮC NGHIỆM|THAM KHẢO|PHẦN\s+.*)?\s*$",
    re.IGNORECASE,
)
