from copy import deepcopy
from typing import Union, Optional, Tuple, List
import re
from docx.document import Document as _Document
from docx.oxml import OxmlElement, ns
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.table import Table
from docx.shared import RGBColor

# --- RICH TEXT UTILS ---

# Unicode Object Replacement Character - used as placeholder for embedded objects
OBJ_CHAR = "\uFFFC"


def _run_has_embedded_content(run_element) -> bool:
    """Check if a w:r element contains embedded content (OLE object, drawing, etc.) without text."""
    has_text = any(True for _ in run_element.iterchildren(ns.qn('w:t')))
    if has_text:
        return False
    # Check for OLE objects (w:object), drawings, or mc:AlternateContent
    for child in run_element:
        tag = child.tag
        if 'object' in tag or 'drawing' in tag or 'AlternateContent' in tag or 'pict' in tag:
            return True
    return False


def _slice_paragraph_runs(original_p: Paragraph, start_char_idx: int, end_char_idx: int) -> OxmlElement:
    """Cắt paragraph giữ nguyên style (Subscript/Superscript/Math/OLE)"""
    new_p = OxmlElement('w:p')
    if original_p.paragraph_format._element.pPr is not None:
        new_p.append(deepcopy(original_p.paragraph_format._element.pPr))
    current_pos = 0
    for run in original_p.runs:
        run_text = run.text or ""
        is_embedded = _run_has_embedded_content(run._element)

        # Embedded content (OLE/drawing) with no text → treat as 1 placeholder char
        if is_embedded and not run_text:
            run_len = 1  # OBJ_CHAR placeholder
        else:
            run_len = len(run_text)

        run_end = current_pos + run_len
        if run_end > start_char_idx and current_pos < end_char_idx:
            if is_embedded and not run_text:
                # Copy the entire embedded run as-is (no slicing needed)
                new_p.append(deepcopy(run._element))
            else:
                # Text run → slice as before
                slice_start = max(0, start_char_idx - current_pos)
                slice_end = min(run_len, end_char_idx - current_pos)
                new_run = deepcopy(run._element)
                t_nodes = new_run.findall(ns.qn('w:t'))
                if t_nodes:
                    sliced_text = run_text[slice_start:slice_end]
                    for t in t_nodes: new_run.remove(t)
                    new_t = OxmlElement('w:t')
                    if sliced_text.strip() == "" and len(sliced_text) > 0:
                        new_t.set(ns.qn('xml:space'), 'preserve')
                    elif " " in sliced_text:
                        new_t.set(ns.qn('xml:space'), 'preserve')
                    new_t.text = sliced_text
                    new_run.append(new_t)
                new_p.append(new_run)
        current_pos += run_len
        if current_pos >= end_char_idx: break
    return new_p


def _create_simple_para_element(text: str) -> OxmlElement:
    p = OxmlElement('w:p')
    r = OxmlElement('w:r')
    t = OxmlElement('w:t')
    if " " in text: t.set(ns.qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    p.append(r)
    return p


# --- DOCX HELPERS ---


def _iter_block_items(doc: _Document):
    """
    Iterate over block items in the document body.
    Yields tuples of (type, block) where type is 'p' for paragraph or 'tbl' for table.
    Tables are NOT flattened - they are yielded as complete table objects.
    """
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield "p", Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield "tbl", Table(child, doc)


def _get_text(block: Union[Paragraph, Table, OxmlElement]) -> str:
    if isinstance(block, Paragraph): return block.text or ""
    # Fallback for raw OxmlElement (CT_P)
    text = ""
    if hasattr(block, 'iter'):
        for node in block.iter():
            if node.tag.endswith('}t'): # Matches w:t in any namespace
                if node.text:
                    text += node.text
    return text


def _clear_body_keep_sectpr(doc: _Document) -> Optional[OxmlElement]:
    body = doc.element.body
    sect_pr = None
    for child in list(body.iterchildren()):
        if child.tag.endswith("sectPr"):
            sect_pr = child
            continue
        body.remove(child)
    return sect_pr


def _append_element(body: OxmlElement, sect_pr: Optional[OxmlElement], element: OxmlElement) -> None:
    if sect_pr is not None:
        sect_pr.addprevious(element)
    else:
        body.append(element)


def _smart_replace_start(paragraph: Paragraph, regex_pattern: re.Pattern, new_prefix: str):
    full_text = paragraph.text
    match = regex_pattern.match(full_text)
    if not match:
        if paragraph.runs:
            paragraph.runs[0].text = new_prefix + paragraph.runs[0].text
        else:
            paragraph.add_run(new_prefix)
        return
    len_to_remove = len(match.group(0))
    current_idx = 0
    replacement_done = False
    for run in paragraph.runs:
        run_text = run.text
        if not run_text: continue
        run_len = len(run_text)
        if current_idx < len_to_remove:
            remove_in_this_run = min(run_len, len_to_remove - current_idx)
            remainder = run_text[remove_in_this_run:]
            if not replacement_done:
                run.text = new_prefix + remainder
                replacement_done = True
            else:
                run.text = remainder
            current_idx += run_len
        else:
            break


def _normalize_format_and_clean(paragraph: Paragraph):
    """Xóa marker và UN-BOLD nội dung để đồng nhất format"""
    for run in paragraph.runs:
        run.underline = False
        run.font.underline = False
        if run.font.color and run.font.color.rgb: run.font.color.rgb = None
        if run.font.highlight_color: run.font.highlight_color = None
        run.font.bold = False


def _recursive_replace_code(element, new_code: str):
    if isinstance(element, CT_P):
        p = Paragraph(element, None)
        text = p.text
        if "Mã đề" in text or "MÃ ĐỀ" in text:
            num_match = re.search(r"\d+", text)
            if num_match:
                old_num = num_match.group(0)
                # Safe run-level replacement (preserves OLE/embedded content)
                for run in p.runs:
                    if old_num in (run.text or ""):
                        run.text = run.text.replace(old_num, new_code)
                        break
                else:
                    # Fallback: no run matched, add new run
                    p.add_run(f" {new_code}")
            else:
                p.add_run(f" {new_code}")
    elif isinstance(element, CT_Tbl):
        table = Table(element, None)
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs: _recursive_replace_code(p._element, new_code)


# --- SMART DETECTION UTILS ---

def _is_run_marked(run: Run) -> bool:
    try:
        if run.underline not in [None, False, 0]: return True
        if run.font.highlight_color: return True
        if run.font.color and run.font.color.rgb:
            if run.font.color.rgb == RGBColor(255, 0, 0): return True
            if str(run.font.color.rgb).upper() == "FF0000": return True
    except Exception:
        pass
    return False


def _build_paragraph_mask(paragraph: Paragraph) -> Tuple[str, List[bool]]:
    full_text = ""
    mask = []
    for run in paragraph.runs:
        text = run.text or ""
        is_marked = _is_run_marked(run)

        # Embedded content (OLE/drawing) with no text → use placeholder char
        if not text and _run_has_embedded_content(run._element):
            full_text += OBJ_CHAR
            mask.append(is_marked)
        else:
            full_text += text
            mask.extend([is_marked] * len(text))
    return full_text, mask
