"""
OMML (Office Math Markup Language) to LaTeX converter.

This module converts Office Math ML XML to LaTeX strings for rendering
mathematical equations from Word documents.
"""

import re
from lxml import etree

# OMML namespace
OMML_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
NSMAP = {'m': OMML_NS}


def omml_to_latex(omml_xml: str) -> str:
    """
    Convert OMML XML string to LaTeX.
    
    Args:
        omml_xml: OMML XML string (e.g., from Word document)
    
    Returns:
        LaTeX string representation of the math expression
    """
    try:
        # Parse the OMML XML
        if isinstance(omml_xml, str):
            root = etree.fromstring(omml_xml.encode('utf-8'))
        else:
            root = etree.fromstring(omml_xml)
        
        # Convert the OMML tree to LaTeX
        latex = _convert_element(root)
        
        # Clean up the result
        latex = _cleanup_latex(latex)
        
        return latex
    except Exception as e:
        print(f"[omml_to_latex] Conversion error: {e}")
        return None


def _get_local_name(element):
    """Get the local name of an element (without namespace)."""
    if element.tag.startswith('{'):
        return element.tag.split('}')[1]
    return element.tag


def _convert_element(element) -> str:
    """Recursively convert an OMML element to LaTeX."""
    tag = _get_local_name(element)
    
    # Main math container
    if tag in ('oMath', 'oMathPara'):
        return ''.join(_convert_element(child) for child in element)
    
    # Run (text container)
    elif tag == 'r':
        return _convert_run(element)
    
    # Fraction
    elif tag == 'f':
        return _convert_fraction(element)
    
    # Radical (square root, nth root)
    elif tag == 'rad':
        return _convert_radical(element)
    
    # Superscript
    elif tag == 'sSup':
        return _convert_superscript(element)
    
    # Subscript
    elif tag == 'sSub':
        return _convert_subscript(element)
    
    # Subscript-Superscript
    elif tag == 'sSubSup':
        return _convert_subsup(element)
    
    # Delimiter (parentheses, brackets, etc.)
    elif tag == 'd':
        return _convert_delimiter(element)
    
    # N-ary operator (sum, product, integral)
    elif tag == 'nary':
        return _convert_nary(element)
    
    # Matrix
    elif tag == 'm':
        return _convert_matrix(element)
    
    # Limit (limit, lim inf, lim sup)
    elif tag == 'limLow':
        return _convert_lim_low(element)
    
    elif tag == 'limUpp':
        return _convert_lim_upp(element)
    
    # Function (sin, cos, etc.)
    elif tag == 'func':
        return _convert_function(element)
    
    # Accent (hat, bar, etc.)
    elif tag == 'acc':
        return _convert_accent(element)
    
    # Bar (overline/underline)
    elif tag == 'bar':
        return _convert_bar(element)
    
    # Grouping character (underbrace, overbrace)
    elif tag == 'groupChr':
        return _convert_group_chr(element)
    
    # Box
    elif tag == 'box':
        return _convert_box(element)
    
    # Equation array
    elif tag == 'eqArr':
        return _convert_eq_array(element)
    
    # Border box
    elif tag == 'borderBox':
        return _convert_border_box(element)
    
    # Pre-sub-superscript
    elif tag == 'sPre':
        return _convert_pre_sub_sup(element)
    
    # Element content (base, numerator, denominator, etc.)
    elif tag in ('e', 'num', 'den', 'deg', 'sub', 'sup', 'lim', 'fName'):
        return ''.join(_convert_element(child) for child in element)
    
    # Text element
    elif tag == 't':
        return _convert_text(element)
    
    # Math run properties - skip
    elif tag in ('rPr', 'ctrlPr', 'argPr', 'fPr', 'radPr', 'sSupPr', 'sSubPr', 
                 'sSubSupPr', 'dPr', 'naryPr', 'mPr', 'limLowPr', 'limUppPr',
                 'funcPr', 'accPr', 'barPr', 'groupChrPr', 'boxPr', 'eqArrPr',
                 'borderBoxPr', 'sPrePr', 'mcs', 'mr'):
        return ''
    
    # Recurse for unknown elements
    else:
        return ''.join(_convert_element(child) for child in element)


def _convert_run(element) -> str:
    """Convert a run element (text content)."""
    result = []
    for child in element:
        tag = _get_local_name(child)
        if tag == 't':
            result.append(_convert_text(child))
    return ''.join(result)


def _convert_text(element) -> str:
    """Convert a text element."""
    text = element.text or ''
    
    # Map special characters to LaTeX
    char_map = {
        '−': '-',
        '×': r'\times ',
        '÷': r'\div ',
        '±': r'\pm ',
        '∓': r'\mp ',
        '≤': r'\leq ',
        '≥': r'\geq ',
        '≠': r'\neq ',
        '≈': r'\approx ',
        '∞': r'\infty ',
        '∑': r'\sum ',
        '∏': r'\prod ',
        '∫': r'\int ',
        '∂': r'\partial ',
        '√': r'\sqrt ',
        'π': r'\pi ',
        'α': r'\alpha ',
        'β': r'\beta ',
        'γ': r'\gamma ',
        'δ': r'\delta ',
        'ε': r'\varepsilon ',
        'ζ': r'\zeta ',
        'η': r'\eta ',
        'θ': r'\theta ',
        'ι': r'\iota ',
        'κ': r'\kappa ',
        'λ': r'\lambda ',
        'μ': r'\mu ',
        'ν': r'\nu ',
        'ξ': r'\xi ',
        'ο': 'o',
        'ρ': r'\rho ',
        'σ': r'\sigma ',
        'τ': r'\tau ',
        'υ': r'\upsilon ',
        'φ': r'\varphi ',
        'χ': r'\chi ',
        'ψ': r'\psi ',
        'ω': r'\omega ',
        'Α': 'A',
        'Β': 'B',
        'Γ': r'\Gamma ',
        'Δ': r'\Delta ',
        'Ε': 'E',
        'Ζ': 'Z',
        'Η': 'H',
        'Θ': r'\Theta ',
        'Ι': 'I',
        'Κ': 'K',
        'Λ': r'\Lambda ',
        'Μ': 'M',
        'Ν': 'N',
        'Ξ': r'\Xi ',
        'Ο': 'O',
        'Π': r'\Pi ',
        'Ρ': 'P',
        'Σ': r'\Sigma ',
        'Τ': 'T',
        'Υ': r'\Upsilon ',
        'Φ': r'\Phi ',
        'Χ': 'X',
        'Ψ': r'\Psi ',
        'Ω': r'\Omega ',
        '→': r'\rightarrow ',
        '←': r'\leftarrow ',
        '↔': r'\leftrightarrow ',
        '⇒': r'\Rightarrow ',
        '⇐': r'\Leftarrow ',
        '⇔': r'\Leftrightarrow ',
        '∈': r'\in ',
        '∉': r'\notin ',
        '⊂': r'\subset ',
        '⊃': r'\supset ',
        '⊆': r'\subseteq ',
        '⊇': r'\supseteq ',
        '∪': r'\cup ',
        '∩': r'\cap ',
        '∅': r'\emptyset ',
        '∀': r'\forall ',
        '∃': r'\exists ',
        '∄': r'\nexists ',
        '∇': r'\nabla ',
        '⋅': r'\cdot ',
        '…': r'\ldots ',
        '⋯': r'\cdots ',
        '⋮': r'\vdots ',
        '⋱': r'\ddots ',
        '′': "'",
        '″': "''",
        '‴': "'''",
        '°': r'^\circ ',
    }
    
    for char, latex in char_map.items():
        text = text.replace(char, latex)
    
    return text


def _convert_fraction(element) -> str:
    """Convert fraction element."""
    num = ''
    den = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'num':
            num = ''.join(_convert_element(c) for c in child)
        elif tag == 'den':
            den = ''.join(_convert_element(c) for c in child)
    return r'\frac{' + num + '}{' + den + '}'


def _convert_radical(element) -> str:
    """Convert radical (root) element."""
    degree = ''
    base = ''
    
    # Check if there's a degree specified
    rad_pr = element.find('m:radPr', namespaces=NSMAP)
    deg_hide = False
    if rad_pr is not None:
        deg_hide_elem = rad_pr.find('m:degHide', namespaces=NSMAP)
        if deg_hide_elem is not None:
            val = deg_hide_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', '0')
            deg_hide = val in ('1', 'true', 'on')
    
    for child in element:
        tag = _get_local_name(child)
        if tag == 'deg':
            degree = ''.join(_convert_element(c) for c in child).strip()
        elif tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
    
    if deg_hide or not degree or degree == '2':
        return r'\sqrt{' + base + '}'
    else:
        return r'\sqrt[' + degree + ']{' + base + '}'


def _convert_superscript(element) -> str:
    """Convert superscript element."""
    base = ''
    sup = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
        elif tag == 'sup':
            sup = ''.join(_convert_element(c) for c in child)
    return base + '^{' + sup + '}'


def _convert_subscript(element) -> str:
    """Convert subscript element."""
    base = ''
    sub = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
        elif tag == 'sub':
            sub = ''.join(_convert_element(c) for c in child)
    return base + '_{' + sub + '}'


def _convert_subsup(element) -> str:
    """Convert subscript-superscript element."""
    base = ''
    sub = ''
    sup = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
        elif tag == 'sub':
            sub = ''.join(_convert_element(c) for c in child)
        elif tag == 'sup':
            sup = ''.join(_convert_element(c) for c in child)
    return base + '_{' + sub + '}^{' + sup + '}'


def _convert_delimiter(element) -> str:
    """Convert delimiter element (parentheses, brackets, etc.)."""
    beg_chr = '('
    end_chr = ')'
    
    # Get delimiter properties
    d_pr = element.find('m:dPr', namespaces=NSMAP)
    if d_pr is not None:
        beg_chr_elem = d_pr.find('m:begChr', namespaces=NSMAP)
        end_chr_elem = d_pr.find('m:endChr', namespaces=NSMAP)
        if beg_chr_elem is not None:
            beg_chr = beg_chr_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', '(')
        if end_chr_elem is not None:
            end_chr = end_chr_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', ')')
    
    # Map delimiter characters to LaTeX
    delim_map = {
        '(': r'\left(',
        ')': r'\right)',
        '[': r'\left[',
        ']': r'\right]',
        '{': r'\left\{',
        '}': r'\right\}',
        '|': r'\left|',
        '⌈': r'\left\lceil',
        '⌉': r'\right\rceil',
        '⌊': r'\left\lfloor',
        '⌋': r'\right\rfloor',
        '〈': r'\left\langle',
        '〉': r'\right\rangle',
        '': '',  # Empty delimiter
    }
    
    left = delim_map.get(beg_chr, r'\left' + beg_chr)
    right = delim_map.get(end_chr, r'\right' + end_chr)
    
    # Get content
    content_parts = []
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            content_parts.append(''.join(_convert_element(c) for c in child))
    
    content = ','.join(content_parts) if len(content_parts) > 1 else (content_parts[0] if content_parts else '')
    
    return left + content + right


def _convert_nary(element) -> str:
    """Convert n-ary element (sum, product, integral, etc.)."""
    operator = r'\int '
    sub = ''
    sup = ''
    base = ''
    
    # Get n-ary properties
    nary_pr = element.find('m:naryPr', namespaces=NSMAP)
    if nary_pr is not None:
        chr_elem = nary_pr.find('m:chr', namespaces=NSMAP)
        if chr_elem is not None:
            char = chr_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', '∫')
            nary_map = {
                '∑': r'\sum',
                '∏': r'\prod',
                '∫': r'\int',
                '∬': r'\iint',
                '∭': r'\iiint',
                '∮': r'\oint',
                '⋃': r'\bigcup',
                '⋂': r'\bigcap',
                '⋁': r'\bigvee',
                '⋀': r'\bigwedge',
            }
            operator = nary_map.get(char, r'\int')
    
    for child in element:
        tag = _get_local_name(child)
        if tag == 'sub':
            sub = ''.join(_convert_element(c) for c in child)
        elif tag == 'sup':
            sup = ''.join(_convert_element(c) for c in child)
        elif tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
    
    result = operator
    if sub:
        result += '_{' + sub + '}'
    if sup:
        result += '^{' + sup + '}'
    result += ' ' + base
    
    return result


def _convert_matrix(element) -> str:
    """Convert matrix element."""
    rows = []
    for child in element:
        tag = _get_local_name(child)
        if tag == 'mr':
            cells = []
            for cell in child:
                cell_tag = _get_local_name(cell)
                if cell_tag == 'e':
                    cells.append(''.join(_convert_element(c) for c in cell))
            rows.append(' & '.join(cells))
    
    return r'\begin{matrix}' + r' \\ '.join(rows) + r'\end{matrix}'


def _convert_lim_low(element) -> str:
    """Convert lower limit element."""
    base = ''
    lim = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
        elif tag == 'lim':
            lim = ''.join(_convert_element(c) for c in child)
    
    # Check if it's a limit function
    if base.strip().lower() in ('lim', 'liminf', 'limsup'):
        return r'\lim_{' + lim + '}'
    
    return base + '_{' + lim + '}'


def _convert_lim_upp(element) -> str:
    """Convert upper limit element."""
    base = ''
    lim = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
        elif tag == 'lim':
            lim = ''.join(_convert_element(c) for c in child)
    
    return base + '^{' + lim + '}'


def _convert_function(element) -> str:
    """Convert function element (sin, cos, etc.)."""
    fname = ''
    arg = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'fName':
            fname = ''.join(_convert_element(c) for c in child).strip()
        elif tag == 'e':
            arg = ''.join(_convert_element(c) for c in child)
    
    # Common functions
    func_map = {
        'sin': r'\sin',
        'cos': r'\cos',
        'tan': r'\tan',
        'cot': r'\cot',
        'sec': r'\sec',
        'csc': r'\csc',
        'arcsin': r'\arcsin',
        'arccos': r'\arccos',
        'arctan': r'\arctan',
        'sinh': r'\sinh',
        'cosh': r'\cosh',
        'tanh': r'\tanh',
        'log': r'\log',
        'ln': r'\ln',
        'lg': r'\lg',
        'exp': r'\exp',
        'lim': r'\lim',
        'min': r'\min',
        'max': r'\max',
        'inf': r'\inf',
        'sup': r'\sup',
        'det': r'\det',
        'dim': r'\dim',
        'ker': r'\ker',
        'gcd': r'\gcd',
        'lcm': r'\text{lcm}',
        'mod': r'\mod',
    }
    
    latex_fname = func_map.get(fname.lower(), r'\text{' + fname + '}')
    
    return latex_fname + ' ' + arg


def _convert_accent(element) -> str:
    """Convert accent element."""
    char = '^'  # Default to hat
    base = ''
    
    acc_pr = element.find('m:accPr', namespaces=NSMAP)
    if acc_pr is not None:
        chr_elem = acc_pr.find('m:chr', namespaces=NSMAP)
        if chr_elem is not None:
            char = chr_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', '^')
    
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
    
    accent_map = {
        '^': r'\hat',
        '̂': r'\hat',
        '~': r'\tilde',
        '̃': r'\tilde',
        '¯': r'\bar',
        '̄': r'\bar',
        '→': r'\vec',
        '⃗': r'\vec',
        '.': r'\dot',
        '̇': r'\dot',
        '..': r'\ddot',
        '̈': r'\ddot',
        '˘': r'\breve',
        '̆': r'\breve',
        'ˇ': r'\check',
        '̌': r'\check',
    }
    
    accent = accent_map.get(char, r'\hat')
    return accent + '{' + base + '}'


def _convert_bar(element) -> str:
    """Convert bar element (overline/underline)."""
    base = ''
    pos = 'top'  # Default to overline
    
    bar_pr = element.find('m:barPr', namespaces=NSMAP)
    if bar_pr is not None:
        pos_elem = bar_pr.find('m:pos', namespaces=NSMAP)
        if pos_elem is not None:
            pos = pos_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', 'top')
    
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
    
    if pos == 'bot':
        return r'\underline{' + base + '}'
    else:
        return r'\overline{' + base + '}'


def _convert_group_chr(element) -> str:
    """Convert grouping character element (underbrace, overbrace)."""
    base = ''
    char = '⏟'  # Default underbrace
    pos = 'bot'
    
    group_pr = element.find('m:groupChrPr', namespaces=NSMAP)
    if group_pr is not None:
        chr_elem = group_pr.find('m:chr', namespaces=NSMAP)
        pos_elem = group_pr.find('m:pos', namespaces=NSMAP)
        if chr_elem is not None:
            char = chr_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', '⏟')
        if pos_elem is not None:
            pos = pos_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', 'bot')
    
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
    
    if char == '⏞' or pos == 'top':
        return r'\overbrace{' + base + '}'
    else:
        return r'\underbrace{' + base + '}'


def _convert_box(element) -> str:
    """Convert box element."""
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            return ''.join(_convert_element(c) for c in child)
    return ''


def _convert_eq_array(element) -> str:
    """Convert equation array element."""
    rows = []
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            rows.append(''.join(_convert_element(c) for c in child))
    
    return r'\begin{aligned}' + r' \\ '.join(rows) + r'\end{aligned}'


def _convert_border_box(element) -> str:
    """Convert border box element."""
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            return r'\boxed{' + ''.join(_convert_element(c) for c in child) + '}'
    return ''


def _convert_pre_sub_sup(element) -> str:
    """Convert pre-subscript-superscript element."""
    base = ''
    sub = ''
    sup = ''
    for child in element:
        tag = _get_local_name(child)
        if tag == 'e':
            base = ''.join(_convert_element(c) for c in child)
        elif tag == 'sub':
            sub = ''.join(_convert_element(c) for c in child)
        elif tag == 'sup':
            sup = ''.join(_convert_element(c) for c in child)
    
    return '{}_{' + sub + '}^{' + sup + '}' + base


def _cleanup_latex(latex: str) -> str:
    """Clean up the generated LaTeX."""
    if not latex:
        return latex
    
    # Remove excessive whitespace
    latex = re.sub(r'\s+', ' ', latex)
    latex = latex.strip()
    
    # Remove empty braces
    latex = re.sub(r'\{\s*\}', '', latex)
    
    # Fix multiple spaces
    latex = re.sub(r'  +', ' ', latex)
    
    return latex
