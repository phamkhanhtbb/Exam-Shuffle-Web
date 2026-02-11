
import re

OBJ_CHAR = "\uFFFC"
# Current regex from constants.py
INLINE_OPTION_PATTERN = re.compile(r"(?:^|(?<![0-9])\s)(\*?)([A-H])[\.\)](\*?)")

test_cases = [
    # Case 1: Standard space
    f"A. Formula {OBJ_CHAR} B. Formula",
    # Case 2: No space, just Object char
    f"A. Formula {OBJ_CHAR}B. Formula",
    # Case 3: Start of line
    "A. Formula",
]

print("Testing Regex:", INLINE_OPTION_PATTERN.pattern)
for i, text in enumerate(test_cases):
    matches = list(INLINE_OPTION_PATTERN.finditer(text))
    labels = [m.group(2) for m in matches]
    print(f"Case {i+1}: '{text.replace(OBJ_CHAR, '<OBJ>')}' -> Found: {labels}")

# Proposed Fix
NEW_PATTERN = re.compile(r"(?:^|(?<![0-9])[\s\uFFFC])(\*?)([A-H])[\.\)](\*?)")
print("\nTesting New Regex:", NEW_PATTERN.pattern)
for i, text in enumerate(test_cases):
    matches = list(NEW_PATTERN.finditer(text))
    labels = [m.group(2) for m in matches]
    print(f"Case {i+1}: '{text.replace(OBJ_CHAR, '<OBJ>')}' -> Found: {labels}")
