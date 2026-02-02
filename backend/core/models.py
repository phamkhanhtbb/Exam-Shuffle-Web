from dataclasses import dataclass, field
from typing import List
from docx.oxml import OxmlElement

# --- DATA STRUCTURES ---
@dataclass
class OptionBlock:
    label: str  # A, B, C, D
    elements: List[OxmlElement] = field(default_factory=list)
    is_correct: bool = False


@dataclass
class QuestionBlock:
    original_idx: int
    raw_label: str
    stem_elements: List[OxmlElement] = field(default_factory=list)
    options: List[OptionBlock] = field(default_factory=list)
    mode: str = "mcq"


@dataclass
class Section:
    title: str
    info_elements: List[OxmlElement] = field(default_factory=list)
    questions: List[QuestionBlock] = field(default_factory=list)


@dataclass
class ExamStructure:
    header_elements: List[OxmlElement] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    footer_elements: List[OxmlElement] = field(default_factory=list)
