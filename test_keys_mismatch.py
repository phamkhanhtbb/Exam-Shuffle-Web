
import sys
import os
import json
from unittest.mock import MagicMock

# Add backend
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.core.models import ExamStructure, Section, QuestionBlock, OptionBlock
from backend.core.generators import _apply_external_key, _build_exam_body
from backend.core import generators

# Mock Docx objects
class MockElement:
    def __init__(self): self.xml = ""
class MockRun:
    def __init__(self, text): 
        self.text = text
        self.font = MagicMock()
class MockParagraph:
    def __init__(self, text):
        self.text = text
        self.runs = [MockRun(text)]
        self._element = MagicMock()
        self._element.tag = 'w:p'
        self.paragraph_format = MagicMock()
    def add_run(self, text): return MockRun(text)

# CONSTANTS Mock
generators.OPTION_START_PATTERN = MagicMock()
generators.OPTION_START_PATTERN.match = lambda x: None # Mock no match to trigger "new label" logic?
# Wait, we want to test _apply_external_key primarily.

def test_key_application():
    print("--- Test 1: External Key Application ---")
    
    # 1. Setup Structure
    # Question 1
    q1 = QuestionBlock(original_idx=1, raw_label="Câu 1")
    q1.options = [
        OptionBlock(label="A.", is_correct=False),
        OptionBlock(label="B.", is_correct=False),
        OptionBlock(label="C.", is_correct=False),
        OptionBlock(label="D.", is_correct=False),
    ]
    q1.mode = "mcq"
    q1.stem_elements = [MockParagraph("Câu 1:")]
    
    # Question 2
    q2 = QuestionBlock(original_idx=2, raw_label="Câu 2")
    q2.options = [
        OptionBlock(label="A.", is_correct=False),
        OptionBlock(label="B.", is_correct=False),
    ]
    q2.mode = "mcq"
    q2.stem_elements = [MockParagraph("Câu 2:")]
    
    structure = ExamStructure()
    sec = Section(title="Phần 1")
    sec.questions = [q1, q2]
    structure.sections = [sec]
    
    # 2. Simulate Map from Frontend (JSON strings)
    # User marks "B" for Q1, "A" for Q2.
    external_map = {
        "1": "B",
        "2": "A"
    }
    
    print(f"External Map: {external_map}")
    
    # 3. Apply Key
    _apply_external_key(structure, external_map)
    
    # 4. Verify Q1
    print("\nChecking Q1 (Expected B=True):")
    opts = structure.sections[0].questions[0].options
    for opt in opts:
        print(f"  {opt.label}: {opt.is_correct}")
    
    if opts[1].is_correct and not opts[0].is_correct:
         print("  [PASS] Q1 Correct.")
    else:
         print("  [FAIL] Q1 FAILED.")

    # 5. Verify Q2
    print("\nChecking Q2 (Expected A=True):")
    opts = structure.sections[0].questions[1].options
    for opt in opts:
        print(f"  {opt.label}: {opt.is_correct}")

    if opts[0].is_correct and not opts[1].is_correct:
         print("  [PASS] Q2 Correct.")
    else:
         print("  [FAIL] Q2 FAILED.")


def test_shuffling_logic():
    print("\n--- Test 2: Shuffling Logic ---")
    # Setup Q1 already marked correct=B (Index 1)
    q1 = QuestionBlock(original_idx=1, raw_label="Câu 1")
    # Using specific objects to track identity
    optA = OptionBlock(label="A.", is_correct=False); optA.elements=[MockParagraph("Content A")]
    optB = OptionBlock(label="B.", is_correct=True);  optB.elements=[MockParagraph("Content B (CORRECT)")]
    optC = OptionBlock(label="C.", is_correct=False); optC.elements=[MockParagraph("Content C")]
    optD = OptionBlock(label="D.", is_correct=False); optD.elements=[MockParagraph("Content D")]
    
    q1.options = [optA, optB, optC, optD]
    q1.mode = "mcq"
    q1.stem_elements = [MockParagraph("Câu 1:")]
    
    structure = ExamStructure()
    sec = Section(title="Phần Test")
    sec.questions = [q1]
    structure.sections = [sec]
    
    # Mock Document
    target_doc = MagicMock()
    target_doc.add_paragraph = lambda: MockParagraph("")
    
    # We need to mock deepcopy to track objects? 
    # Or just rely on logic.
    # _build_exam_body deepcopies questions.
    
    # Mocking _process_mcq_option_format to do nothing (avoid oxml errors)
    generators._process_mcq_option_format = lambda opt, lbl: None
    generators._create_simple_para_element = lambda x: MagicMock()
    generators._append_element = lambda x,y,z: None
    generators.Paragraph = lambda x,y: MockParagraph("Dummy")
    generators.OxmlElement = lambda x: MagicMock()

    # Run
    # seed=1 fixes the shuffle.
    # Let's inspect what the shuffle order is.
    # Python Random shuffle on [0,1,2,3] with seed 1?
    # We will just capture the return.
    
    q_idx, answers = _build_exam_body(MagicMock(), MagicMock(), target_doc, structure, seed=12345)
    
    print(f"Generated Answers: {answers}")
    
    # Verification:
    # If the answer is, say, "C", then the option at position C (index 2) MUST be the one that has is_correct=True.
    # Since we deepcopied, we can't easily check identity unless we check the text "Content B" matches the position.
    # But _build_exam_body doesn't return the content.
    # It returns 'answers'.
    # If logic is correct, 'answers' should not contain 'X'.
    
    if "X" not in answers:
        print(f" [PASS] Shuffling produced an answer: {answers[0]}")
    else:
        print(" [FAIL] Shuffling produced 'X'!")

if __name__ == "__main__":
    test_key_application()
    test_shuffling_logic()
