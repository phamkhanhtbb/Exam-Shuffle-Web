"""
Preview Service — handles the full preview pipeline:
document parsing, answer detection, structure rendering, and serialization.
"""
import io
import time
import asyncio
import logging

from docx import Document
from docx.text.paragraph import Paragraph as DocxParagraph
from docx.table import Table as DocxTable
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

from fastapi import HTTPException

from docx_serializer import DocxSerializer
from core import parse_exam_template
from exceptions import (
    ExamError,
    TableParseError,
    ParagraphParseError,
    RenderingError,
)
from schemas import PreviewData
from services.answer_parser import extract_answers_from_structure

logger = logging.getLogger("server.preview")


def render_element(el, serializer: DocxSerializer) -> str:
    """Render a single document element (paragraph or table) to text."""
    try:
        if isinstance(el, CT_P):
            para = DocxParagraph(el, serializer.doc)
            return serializer._process_paragraph(para)
        elif isinstance(el, CT_Tbl):
            tbl = DocxTable(el, serializer.doc)
            return serializer._process_table(tbl)
    except Exception as e:
        element_type = "table" if isinstance(el, CT_Tbl) else "paragraph"
        logger.warning(f"Failed to render {element_type} element: {e}")
        if isinstance(el, CT_Tbl):
            raise TableParseError(f"Lỗi xử lý bảng: {e}")
        else:
            raise ParagraphParseError(f"Lỗi xử lý đoạn văn: {e}")
    return ""


def render_structure(structure, serializer: DocxSerializer) -> str:
    """
    Render parsed ExamStructure to text with embedded [ID:hash] tags.
    Uses DocxSerializer for element rendering (math, images, etc).
    """
    lines: list[str] = []

    try:
        for sec in structure.sections:
            # 1. Section Title
            if sec.title:
                lines.append(sec.title)

            # 2. Info Elements (instructions, etc.)
            for el in sec.info_elements:
                try:
                    text = render_element(el, serializer)
                    if text:
                        lines.append(text)
                except (TableParseError, ParagraphParseError) as e:
                    logger.warning(f"Skipping info element due to error: {e.message}")
                    continue

            # 3. Questions
            for q in sec.questions:
                id_tag = f"[ID:{q.content_hash}] " if q.content_hash else ""

                # Render Stem
                for i, el in enumerate(q.stem_elements):
                    try:
                        text = render_element(el, serializer)
                    except (TableParseError, ParagraphParseError) as e:
                        logger.warning(f"Error rendering stem element for question: {e.message}")
                        text = ""
                    if i == 0:
                        text = id_tag + text
                    if text:
                        lines.append(text)

                # Render Options
                for opt in q.options:
                    opt_texts = []
                    for el in opt.elements:
                        try:
                            t = render_element(el, serializer)
                            if t:
                                opt_texts.append(t)
                        except (TableParseError, ParagraphParseError) as e:
                            logger.warning(f"Error rendering option element: {e.message}")
                    if opt_texts:
                        lines.append(" ".join(opt_texts))

                # Emit short answer line if available
                if q.correct_answer_text and q.mode == 'short':
                    lines.append(f"Đáp án: {q.correct_answer_text}")

    except (TableParseError, ParagraphParseError):
        raise  # Re-raise specific parse errors
    except Exception as e:
        raise RenderingError(f"Lỗi khi render cấu trúc đề thi: {e}")

    return "\n".join(lines)


async def process_preview(contents: bytes) -> PreviewData:
    """
    Full preview pipeline:
    1. Open DOCX document
    2. Parse exam structure
    3. Detect answers from structure
    4. Render structure to text with IDs
    5. Return PreviewData with text, assets, and question count
    """
    t0 = time.perf_counter()

    # 1. Open document
    file_stream = io.BytesIO(contents)
    try:
        doc = Document(file_stream)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="File không hợp lệ hoặc bị lỗi (Không phải file DOCX chuẩn)",
        )

    t1 = time.perf_counter()
    logger.info(f"[PERF] Document open: {t1 - t0:.3f}s")

    # 2. Parse structure
    try:
        structure = await asyncio.to_thread(parse_exam_template, contents, doc)
    except Exception as e:
        logger.error(f"Structure parsing failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Lỗi đọc cấu trúc đề thi: {str(e)}",
        )

    t2 = time.perf_counter()
    logger.info(f"[PERF] Structure parsing: {t2 - t1:.3f}s")

    # 3. Detect answers from structure (optional, non-fatal)
    answer_map: dict = {}
    try:
        answer_map = extract_answers_from_structure(structure)
        logger.info(f"Auto-detected {len(answer_map)} answers for marking.")
    except Exception as e:
        logger.warning(f"Auto-marking extraction failed (ignoring): {e}")

    # 4. Render structure
    serializer = DocxSerializer(doc, answer_map=answer_map)
    loop = asyncio.get_event_loop()
    raw_text = await loop.run_in_executor(None, render_structure, structure, serializer)

    t3 = time.perf_counter()
    logger.info(f"[PERF] Rendering: {t3 - t2:.3f}s")
    logger.info(f"[PERF] Total preview: {t3 - t0:.3f}s")

    # 5. Build result
    total_questions = sum(len(sec.questions) for sec in structure.sections)

    return PreviewData(
        raw_text=raw_text,
        assets_map=serializer.assets,
        question_count=total_questions,
    )
