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

def _slice_paragraph_runs(original_p: Paragraph, start_char_idx: int, end_char_idx: int) -> OxmlElement:
    """Cắt paragraph giữ nguyên style (Subscript/Superscript/Math)"""
    new_p = OxmlElement('w:p')
    if original_p.paragraph_format._element.pPr is not None:
        new_p.append(deepcopy(original_p.paragraph_format._element.pPr))
    current_pos = 0
    for run in original_p.runs:
        run_len = len(run.text)
        run_end = current_pos + run_len
        if run_end > start_char_idx and current_pos < end_char_idx:
            slice_start = max(0, start_char_idx - current_pos)
            slice_end = min(run_len, end_char_idx - current_pos)
            new_run = deepcopy(run._element)
            t_nodes = new_run.findall(ns.qn('w:t'))
            if t_nodes:
                text_content = run.text
                sliced_text = text_content[slice_start:slice_end]
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
    Iterate over block items, but FLATTEN tables into their constituent paragraphs.
    This ensures that content inside tables is parsed linearly just like the frontend editor text.
    """
    def _recurse_element(element):
        if isinstance(element, CT_P):
            yield "p", Paragraph(element, doc)
        elif isinstance(element, CT_Tbl):
            table = Table(element, doc)
            for row in table.rows:
                for cell in row.cells:
                    # Recursively process cell content
                    # Note: Cell content is usually paragraphs or (nested) tables
                    for child in cell._element.iterchildren():
                        if isinstance(child, CT_P):
                            yield "p", Paragraph(child, doc)
                        elif isinstance(child, CT_Tbl):
                             yield from _recurse_element(child)

    for child in doc.element.body.iterchildren():
        yield from _recurse_element(child)


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
                p.text = text.replace(num_match.group(0), new_code)
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
    except:
        pass
    return False


def _build_paragraph_mask(paragraph: Paragraph) -> Tuple[str, List[bool]]:
    full_text = ""
    mask = []
    for run in paragraph.runs:
        text = run.text
        is_marked = _is_run_marked(run)
        full_text += text
        mask.extend([is_marked] * len(text))
    return full_text, mask
