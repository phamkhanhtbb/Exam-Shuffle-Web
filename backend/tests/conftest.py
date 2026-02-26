"""
Pytest configuration and shared fixtures for the ExamShuffling backend tests.
"""

import os
import pytest

# Set dummy environment variables BEFORE any app imports
# This prevents boto3/config from failing during test collection
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_REGION", "ap-southeast-1")
os.environ.setdefault("AWS_S3_BUCKET_INPUT", "test-bucket-input")
os.environ.setdefault("AWS_S3_BUCKET_OUTPUT", "test-bucket-output")
os.environ.setdefault(
    "AWS_SQS_QUEUE_URL",
    "https://sqs.ap-southeast-1.amazonaws.com/000000000000/test-queue",
)
os.environ.setdefault("AWS_DYNAMODB_TABLE", "TestTable")


@pytest.fixture
def sample_mcq_text():
    """Sample MCQ question text for testing parser logic."""
    return """Phần I. TRẮC NGHIỆM
Câu 1. Đâu là thủ đô của Việt Nam?
A. Hồ Chí Minh
*B. Hà Nội
C. Đà Nẵng
D. Huế
Câu 2. 1 + 1 = ?
A. 1
*B. 2
C. 3
D. 4"""


@pytest.fixture
def sample_tf_text():
    """Sample True/False question text for testing parser logic."""
    return """Phần II. ĐÚNG SAI
Câu 1. Xét các mệnh đề sau:
a) Trái đất quay quanh mặt trời
b) Nước sôi ở 50 độ C
c) 2 + 2 = 4
d) Mặt trời mọc ở phía Tây"""
