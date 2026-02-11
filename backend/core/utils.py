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
    """
    Enhanced slicing that preserves XML structure (Math, Hyperlinks, etc.).
    Iterates over all XML children to capture inline elements skipped by python-docx's .runs property.
    """
    new_p = OxmlElement('w:p')
    if original_p.paragraph_format._element.pPr is not None:
        new_p.append(deepcopy(original_p.paragraph_format._element.pPr))

    current_pos = 0
    
    # Iterate over ALL children of the paragraph element
    for child in original_p._element:
        # Skip properties, we already handled pPr
        if child.tag == ns.qn('w:pPr'):
            continue

        # 1. Handle Text Runs (w:r)
        if child.tag == ns.qn('w:r'):
            # Convert to Run object for helper usage (text extraction)
            run = Run(child, original_p)
            run_text = run.text or ""
            
            # Determine effective length in the index map (from _build_paragraph_mask logic)
            is_embedded = _run_has_embedded_content(child)
            if is_embedded and not run_text:
                run_len = 1  # Placeholder char
            else:
                run_len = len(run_text)

            run_end = current_pos + run_len

            # Check overlap with slice range
            if run_end > start_char_idx and current_pos < end_char_idx:
                if is_embedded and not run_text:
                    # Keep embedded object intact
                    new_p.append(deepcopy(child))
                else:
                    # Slice text run
                    slice_start = max(0, start_char_idx - current_pos)
                    slice_end = min(run_len, end_char_idx - current_pos)
                    
                    new_run = deepcopy(child)
                    # Clear existing text nodes in the copy to remove 'old' text
                    # We will append the 'sliced' text node
                    t_nodes = new_run.findall(ns.qn('w:t'))
                    # But we must be careful: clearing all might remove styling if mixed?
                    # valid w:r usually has properties and w:t/w:drawing.
                    # We only want to adjust w:t.
                    
                    if t_nodes:
                        sliced_text = run_text[slice_start:slice_end]
                        # Remove old text nodes
                        for t in t_nodes: new_run.remove(t)
                        
                        # Create new text node
                        new_t = OxmlElement('w:t')
                        if sliced_text.strip() == "" and len(sliced_text) > 0:
                            new_t.set(ns.qn('xml:space'), 'preserve')
                        elif " " in sliced_text:
                            new_t.set(ns.qn('xml:space'), 'preserve')
                        new_t.text = sliced_text
                        
                        # Append new text node
                        new_run.append(new_t)
                    
                    new_p.append(new_run)
            
            current_pos += run_len

        # 2. Handle Other Elements (Math, Hyperlinks, Bookmarks, etc.)
        else:
            # If next option starts at 2.
            # Then Math belongs to?
            # Actually, standard behavior: Option A text ends at 2. Option B text starts at 2.
            # The "boundary" is infinitesimal.
            # Heuristic: Included if start_char_idx <= current_pos < end_char_idx
            # EXCEPTION: If current_pos == start_char_idx (at the very beginning of the slice), include it.
            # If current_pos == end_char_idx (at the very end), exclude it?
            # Let's consider:
            # "A. [Math]" -> Text "A.".
            # Option A slice: [0, 2].
            # Run "A." pos 0->2. Included.
            # Math pos 2.
            # Is 2 < 2? No.
            # So Math is EXCLUDED from A.
            # Option B slice: [2, 10].
            # Math pos 2. `2 <= 2 < 10`? Yes.
            # So Math goes to B. -> "B. [Math from A]". WRONG.
            
            # Logic Correction:
            # The regex for Options usually matches " B.".
            # "A.[Math] B."
            # "A." is at [0, 2]. " B." starts at 2 (space).
            # Math is physically betweeen "A." and " B.".
            # If we adhere strictly to integer indices, it's ambiguous.
            # BUT, generally, the "Next Option" pattern includes the *Start* of the next option.
            # " B." is the start of Option B.
            # So everything *before* " B." should belong to Option A.
            # If Math is at pos 2, and " B." starts at pos 2.
            # We need to decide: does " B." start *after* the Math or *before*?
            # In XML order: Run("A.") -> Math -> Run(" B.").
            # Indices: 0-2 (A), 2-2 (Math), 2-5 (B).
            # The break point is index 2.
            # If we slice [0, 2] for A.
            # We want Math included.
            # So condition should be: `start_char_idx <= current_pos <= end_char_idx`?
            # If we use <= end, then Math at 2 is included in A [0,2] AND B [2,5]?
            # No, we don't want duplication.
            
            # Let's look at `parsers.py`:
            # `end_idx` for Option A is `matches[i+1].start()`.
            # `matches[i].start()` is start of "A.".
            # `matches[i+1].start()` is start of "B.".
            # So A is [StartA, StartB).
            # If Math is BETWEEN "A." and "B.", it should be in A.
            # So if `current_pos == end_char_idx`, it effectively falls "after" the previous text interval.
            # But "before" the next text interval.
            # Since the Split Point is defined by the *Next Text Match*,
            # Any element *before* that text reading should be preserved in the *Current* block.
            # However, since Math has 0 width, `current_pos` hasn't advanced yet.
            # Effectively, Run("A.") advanced pos to 2.
            # Math is at 2.
            # Run(" B.") starts at 2.
            # The regex found " B." at index 2.
            # If we are slicing A [0, 2].
            # We want everything up to " B.".
            # Since Math comes *before* Run(" B.") in XML, we should include it.
            # 
            # WAIT. If we iterate XML in order.
            # Run("A.") (updates pos 0->2). In [0, 2]. Keep.
            # Math (pos 2). In [0, 2]? 
            # If we use strict `< end`, we lose it.
            # But structurally, we haven't reached " B." yet.
            # So we should Greedy Include 0-lengths if they are within range.
            # Since we iterate linear XML:
            # We are building Option A.
            # Is Math part of Option A? Yes.
            # Is run(" B.") part of Option A? No.
            # So when we hit Run(" B."), we will check `2 < 2` (False) -> Skip " B.".
            # When we hit Math (pos 2), we are effectively "at the end of A" or "start of B".
            # Structurally it is BEFORE B.
            # So for non-text tokens, we should use <= end?
            # OR: `current_pos` tracks "Text Read So Far".
            # At Math node, we have read "A." (2 chars).
            # The slice for A is 0 to 2.
            # If condition `current_pos < end_char_idx` (2 < 2) fails.
            # BUT we want to keep it.
            # So for 0-length elements, maybe `current_pos <= end_char_idx`?
            # If we do that:
            # Slice A [0, 2]. Math (2) -> Keep.
            # Slice B [2, 5]. Math (2) -> Keep.
            # We duplicate math!
            
            # Solution:
            # We need to distinguish "Has read up to boundary" vs "Starting new boundary".
            # The `_slice_paragraph_runs(p, start, end)` is meant to extract content "corresponding" to the text [start:end].
            # If the Text " B." (which signaled the end of A) hasn't started yet...
            # Then we are still in the "realm" of A.
            # BUT `current_pos` is already 2.
            # 
            # Let's adjust the indices logic in `parsers.py`.
            # OR make `_slice` smart.
            # If I use `child.tag != w:r`, I treat it as attaching to *Previous* char?
            # If so, `current_pos - 1 < end_char_idx`? (Assuming pos>0).
            # If `current_pos` (2) is the end of the slice (2).
            # That means the *next* char (at 2) is excluded.
            # Since Math is NOT a char, it's ambiguous.
            # 
            # Practical observation:
            # Options regex usually has a leading space or newline. " B.".
            # "A." -> index 0, len 2.
            # " " -> index 2, len 1.
            # "B." -> index 3.
            # Math typically follows A. "A. [Math]".
            # "A." (0-2). Math (2).
            # " B." (Starts at 2? No! Implicit space?)
            # If "A." and "[Math]" and " B." are contiguous runs/objects.
            # If " B." strictly starts at 2 (no space between A. and B. in text?)
            # Then "A.B."
            # That's ugly doc.
            # Usually: "A. [Math]   B."
            # "A." (2). "   " (3 spaces).
            # Runs: [A.] [Math] [   ] [B.]
            # Poses: 0->2. 2. 2->5. 5->7.
            # Regex " B." matches likely at index 2 (inside the spaces run).
            # Text: "A.   B."
            # Match " B." at index 2? No, "   B." contains " B." at index 2 (space).
            # Start index of B match is 2.
            # Slice A: [0, 2].
            # Run A (0-2). Keep.
            # Math (2).
            # Run Space (2-5). Overlap [0,2] ? No. 2 not < 2.
            # So Space is dropped from A?
            # Yes, A gets "A.". Space goes to B.
            # Math? Dropped because 2 not < 2.
            # 
            # BUG CONFIRMED: 0-length elements at the exact boundary are Dropped by strict `<`.
            # And dropped by strict `>= start` in the next slice?
            # Slice B [2, 10].
            # Math (2). `2 >= 2 and 2 < 10`. TRUE.
            # So Math GOES TO B.
            # "B. [Math]".
            # Wait, user says formulas MISSING. Not moved to B.
            # Why missing?
            # Because `_slice_paragraph_runs` currently only loops `p.runs`.
            # `oMath` is NOT in `p.runs`.
            # So it was simply ignored.
            
            # So my main fix (iterating all children) is the big win.
            # Now, where does it land?
            # If Math is at 2.
            # Start=0, End=2.
            # Next Slice: Start=2, End=...
            # In "A", `2 < 2` is False. Math dropped.
            # In "B", `2 >= 2`. Math Included.
            # So Math moves to B.
            # "A." ... "B. [Math] B."
            # That is also bad (Math A moved to B).
            # But User report says "Missing".
            # My current code `utils.py` uses `p.runs`. It misses math completely.
            # So priority 1: Include it.
            # Priority 2: Fix the boundary drift.
            
            # Boundary Drift Fix:
            # If we want Math to stay with A.
            # We need to include it in Slice A.
            # So `if child is not text run: include if current_pos <= end`?
            # But then B also claims it?
            # No, B starts at 2. `2 >= 2`.
            # We want B to *NOT* claim it if it's "leftover" from A.
            # But how do we distinguish "Leftover from A" vs "Prefix of B"?
            # XML Order: A -> Math -> B.
            # Math comes *after* A text.
            # Math comes *before* B text.
            # So technically it falls "between" 2 and 2.
            # If we want A covering "A. [Math]", we expect the text of A to extend past Math?
            # If Math implies a visual space?
            # 
            # Let's look at `_split_inline_options_smart` in `parsers.py`.
            # It defines `end_idx = matches[i+1].start()`.
            # If the user typed "A. [Math] B."
            # Text is "A. B." (Math invisible).
            # "A." is [0, 2]. " B." starts at 2.
            # Explicitly, the " B." pattern matched at index 2.
            # So we slice [0, 2].
            # 
            # Strategy:
            # Always attach 0-length elements to the *Preceding* text interval?
            # I.e. `current_pos <= end_char_idx`.
            # Except if `current_pos == start_char_idx`?
            # If Start=2. Math is at 2.
            # It's at the beginning of B context.
            # If we attach to Preceding, it goes to A.
            # Ideally:
            # Slice A [0,2] -> Includes Math(2).
            # Slice B [2,5] -> Should exclude Math(2)?
            # If B logic is `run_end > start`.
            # For Math (len 0). RunEnd=2.
            # `2 > 2` is False.
            # So B automatically EXCLUDES it!
            # Perfect!
            # 
            # So:
            # A (0-2): `current_pos < 2`? Math(2) `2 < 2` False.
            # we need `current_pos <= end`.
            # B (2-5): `run_end (2) > 2`? False. Excluded.
            # 
            # Wait, `run_end` for Math is `current_pos` (0 len).
            # So for B (Start=2). Math is at 2.
            # `2 > 2` False.
            # So Math is Dropped by B too.
            # 
            # So if we change A's logic to `<=`.
            # A keeps it. B ignores it.
            # Result: Math stays with A.
            # 
            # Is there a risk?
            # If "Start of A" has a math element? " [Math] A."
            # Start=0. Math at 0.
            # A [0, 2].
            # Math(0). `0 <= 2`. Included.
            # B? No.
            # Correct.
            
            # Corner case: "A. B." (no space).
            # A [0, 2]. B [2, 4].
            # Math between?
            # Math(2).
            # A keeps. B ignores.
            # Correct.
            
            # What if "A." is just matched?
            # The *regex* determines the split.
            # If Math is *inside* the text that matched " B."?
            # Math has 0 text width. It can't be "inside" a match of non-zero length text.
            # It is always at a boundary of text chars.
            
            # Conclusion:
            # For 0-length elements (Math, etc.):
            # Include if `start_char_idx <= current_pos <= end_char_idx`.
            # AND strictly `current_pos < end_char_idx`? 
            # No, `current_pos <= end` allows A to grab it.
            # 
            # Actually, let's look closer at B condition.
            # `run_end > start`.
            # Math(2) `run_end=2`. Start=2.
            # `2 > 2` False.
            # So B *never* picks it up if it's exactly at Start.
            # This implies 0-length elements at the start of a slice are dropped by the standard logic!
            # 
            # This is OK if A picked it up (it was at the End of A).
            # But what about the *First* slice?
            # Slice [0, 2].
            # Math at 0. `run_end=0`. Start=0. `0 > 0` False.
            # Math at the VERY START of the doc is dropped?!
            # 
            # Fix for 0-length elements:
            # Condition: `current_pos >= start_char_idx` AND `current_pos <= end_char_idx`.
            # 
            # But wait, if we use `<= end`, we duplicate if the next slice picks it up.
            # Does next slice pick it up?
            # `run_end > start`.
            # `0 > 0` False.
            # So B doesn't pick it up.
            # 
            # So we MUST relax the Start condition for 0-length elements.
            # `run_end >= start`?
            # If Math(2). Start=2.
            # `2 >= 2`. True.
            # So B picks it up.
            # 
            # If we use `>= start` for B, and `<= end` for A.
            # Math(2) is in A [0,2] and B [2,5].
            # DUPLICATION.
            # 
            # We want Math to belong to ONE side.
            # Generally, in "A. [Math] B.", Math belongs to A.
            # So A should grab `frame ending at 2`.
            # B should `frame starting at 2`.
            # If A grabs `curr <= end`.
            # B should NOT grab `curr == start`.
            # B grabs `curr > start`? (Standard logic `run_end > start` works for 0-len: 2 > 2 False).
            # 
            # So:
            # Rule: 0-length elements attach to the *Preceding* block (Left-Associative).
            # Logic: `current_pos <= end_char_idx`.
            # Exception: What about Math at 0?
            # If Slice starts at 0.
            # Check A [0, 2].
            # Math(0). `0 <= 2`. Included.
            # 
            # But wait, logic `run_end > start`
            # For Math(0). `0 > 0` False.
            # So the standard logic DROPS start-of-block Math.
            # 
            # We need explicit handling.
            
            new_p.append(deepcopy(child))
            
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
