"""
Unit tests for the core parser module.
Tests hash generation, answer extraction, and basic parsing logic.
"""
import pytest
from core.parsers import _generate_content_hash


class TestContentHash:
    """Test the content hash generation for question matching."""

    def test_hash_returns_string(self):
        result = _generate_content_hash("Câu 1. Test question")
        assert isinstance(result, str)

    def test_hash_length(self):
        """Hash should be 12 characters (truncated MD5)."""
        result = _generate_content_hash("Câu 1. Test question")
        assert len(result) == 12

    def test_hash_deterministic(self):
        """Same input should always produce same hash."""
        text = "Đâu là thủ đô của Việt Nam?"
        h1 = _generate_content_hash(text)
        h2 = _generate_content_hash(text)
        assert h1 == h2

    def test_hash_different_for_different_input(self):
        h1 = _generate_content_hash("Question 1")
        h2 = _generate_content_hash("Question 2")
        assert h1 != h2

    def test_hash_case_insensitive(self):
        """Hash should normalize to lowercase."""
        h1 = _generate_content_hash("ABC DEF")
        h2 = _generate_content_hash("abc def")
        assert h1 == h2

    def test_hash_whitespace_insensitive(self):
        """Hash should collapse whitespace."""
        h1 = _generate_content_hash("hello   world")
        h2 = _generate_content_hash("hello world")
        assert h1 == h2
