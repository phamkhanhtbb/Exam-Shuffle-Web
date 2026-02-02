class ExamError(Exception):
    """Base exception for exam processing errors"""
    def __init__(self, message: str, code: str = "EXAM_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class InvalidExamFormatException(ExamError):
    def __init__(self, message="Định dạng đề thi không hợp lệ. Vui lòng kiểm tra lại cấu trúc."):
        super().__init__(message, "INVALID_FORMAT")

class AnswerKeyNotFoundError(ExamError):
    def __init__(self, message="Không tìm thấy bảng đáp án hoặc từ khóa 'ĐÁP ÁN'. Vui lòng kiểm tra lại file."):
        super().__init__(message, "NO_ANSWER_KEY")

class FontError(ExamError):
    def __init__(self, message="File chứa font chữ không được hỗ trợ hoặc bị lỗi."):
        super().__init__(message, "FONT_ERROR")

class EmptyQuestionError(ExamError):
    def __init__(self, message="Không tìm thấy câu hỏi nào trong đề thi. Vui lòng kiểm tra lại các từ khóa 'Câu', 'Bài'."):
        super().__init__(message, "NO_QUESTIONS")
