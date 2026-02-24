"""
Custom Exceptions for Exam Processing.

This module defines a hierarchy of exceptions to handle various error 
scenarios during DOCX parsing, randomization, and conversion.
"""

class ExamError(Exception):
    """
    Base exception for all exam-related errors.
    Includes a human-readable message and a machine-readable error code.
    """
    def __init__(self, message: str, code: str = "EXAM_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class InvalidExamFormatException(ExamError):
    """Raised when the document structure doesn't match expected patterns."""
    def __init__(self, message="Định dạng đề thi không hợp lệ. Vui lòng kiểm tra lại cấu trúc."):
        super().__init__(message, "INVALID_FORMAT")

class AnswerKeyNotFoundError(ExamError):
    """Raised when the 'ĐÁP ÁN' section is missing or unparseable."""
    def __init__(self, message="Không tìm thấy bảng đáp án hoặc từ khóa 'ĐÁP ÁN'. Vui lòng kiểm tra lại file."):
        super().__init__(message, "NO_ANSWER_KEY")

class FontError(ExamError):
    """Raised when unsupported or corrupted fonts are encountered."""
    def __init__(self, message="File chứa font chữ không được hỗ trợ hoặc bị lỗi."):
        super().__init__(message, "FONT_ERROR")

class EmptyQuestionError(ExamError):
    """Raised when no valid questions are identified in the document."""
    def __init__(self, message="Không tìm thấy câu hỏi nào trong đề thi. Vui lòng kiểm tra lại các từ khóa 'Câu', 'Bài'."):
        super().__init__(message, "NO_QUESTIONS")

class TableParseError(ExamError):
    """Raised during errors in processing complex DOCX tables."""
    def __init__(self, message="Lỗi xử lý bảng trong đề thi."):
        super().__init__(message, "TABLE_PARSE_ERROR")

class ParagraphParseError(ExamError):
    """Raised during general text/paragraph processing failures."""
    def __init__(self, message="Lỗi xử lý đoạn văn trong đề thi."):
        super().__init__(message, "PARAGRAPH_PARSE_ERROR")

class RenderingError(ExamError):
    """Raised during the final step of generating the output ZIP/DOCX files."""
    def __init__(self, message="Lỗi khi render cấu trúc đề thi."):
        super().__init__(message, "RENDERING_ERROR")
