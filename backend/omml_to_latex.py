"""
OMML (Office Math Markup Language) to LaTeX converter
Extracts text content from OMML and converts to LaTeX-like format
"""
import re
from lxml import etree

# Namespaces for OMML
NAMESPACES = {
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
}

# Greek letter mapping (Unicode to LaTeX)
GREEK_MAP = {
    'α': '\\alpha', 'β': '\\beta', 'γ': '\\gamma', 'δ': '\\delta',
    'ε': '\\epsilon', 'ζ': '\\zeta', 'η': '\\eta', 'θ': '\\theta',
    'ι': '\\iota', 'κ': '\\kappa', 'λ': '\\lambda', 'μ': '\\mu',
    'ν': '\\nu', 'ξ': '\\xi', 'π': '\\pi', 'ρ': '\\rho',
    'σ': '\\sigma', 'τ': '\\tau', 'υ': '\\upsilon', 'φ': '\\phi',
    'χ': '\\chi', 'ψ': '\\psi', 'ω': '\\omega',
    'Γ': '\\Gamma', 'Δ': '\\Delta', 'Θ': '\\Theta', 'Λ': '\\Lambda',
    'Ξ': '\\Xi', 'Π': '\\Pi', 'Σ': '\\Sigma', 'Υ': '\\Upsilon',
    'Φ': '\\Phi', 'Ψ': '\\Psi', 'Ω': '\\Omega',
}

# Math symbol mapping
SYMBOL_MAP = {
    '≤': '\\leq', '≥': '\\geq', '≠': '\\neq', '≈': '\\approx',
    '∞': '\\infty', '∂': '\\partial', '∇': '\\nabla',
    '±': '\\pm', '∓': '\\mp', '×': '\\times', '÷': '\\div',
    '∈': '\\in', '∉': '\\notin', '⊂': '\\subset', '⊃': '\\supset',
    '∪': '\\cup', '∩': '\\cap', '→': '\\rightarrow', '←': '\\leftarrow',
    '↔': '\\leftrightarrow', '⇒': '\\Rightarrow', '⇐': '\\Leftarrow',
    '⇔': '\\Leftrightarrow', '∀': '\\forall', '∃': '\\exists',
    '∅': '\\emptyset', '∴': '\\therefore', '∵': '\\because',
    '⊥': '\\perp', '∥': '\\parallel', '∠': '\\angle',
    '°': '^{\\circ}', '′': "'", '″': "''",
    '√': '\\sqrt', '∑': '\\sum', '∏': '\\prod', 
    '∫': '\\int', '∮': '\\oint',
}


def convert_symbols(text: str) -> str:
    """Convert Unicode Greek letters and math symbols to LaTeX commands"""
    result = text
    for char, cmd in GREEK_MAP.items():
        result = result.replace(char, cmd + ' ')
    for char, cmd in SYMBOL_MAP.items():
        result = result.replace(char, cmd + ' ')
    return result


def process_element(elem) -> str:
    """
    Recursively process an OMML element and convert to LaTeX
    """
    tag = etree.QName(elem.tag).localname if elem.tag else ''
    result = ''
    
    # Fraction: m:f
    if tag == 'f':
        num = elem.find('m:num', namespaces=NAMESPACES)
        den = elem.find('m:den', namespaces=NAMESPACES)
        num_text = process_children(num) if num is not None else ''
        den_text = process_children(den) if den is not None else ''
        return f'\\frac{{{num_text}}}{{{den_text}}}'
    
    # Radical/Square root: m:rad
    if tag == 'rad':
        deg = elem.find('m:deg', namespaces=NAMESPACES)
        e = elem.find('m:e', namespaces=NAMESPACES)
        e_text = process_children(e) if e is not None else ''
        deg_text = process_children(deg) if deg is not None else ''
        if deg_text and deg_text.strip():
            return f'\\sqrt[{deg_text}]{{{e_text}}}'
        return f'\\sqrt{{{e_text}}}'
    
    # Superscript: m:sSup
    if tag == 'sSup':
        base = elem.find('m:e', namespaces=NAMESPACES)
        sup = elem.find('m:sup', namespaces=NAMESPACES)
        base_text = process_children(base) if base is not None else ''
        sup_text = process_children(sup) if sup is not None else ''
        return f'{base_text}^{{{sup_text}}}'
    
    # Subscript: m:sSub
    if tag == 'sSub':
        base = elem.find('m:e', namespaces=NAMESPACES)
        sub = elem.find('m:sub', namespaces=NAMESPACES)
        base_text = process_children(base) if base is not None else ''
        sub_text = process_children(sub) if sub is not None else ''
        return f'{base_text}_{{{sub_text}}}'
    
    # Sub-Superscript: m:sSubSup
    if tag == 'sSubSup':
        base = elem.find('m:e', namespaces=NAMESPACES)
        sub = elem.find('m:sub', namespaces=NAMESPACES)
        sup = elem.find('m:sup', namespaces=NAMESPACES)
        base_text = process_children(base) if base is not None else ''
        sub_text = process_children(sub) if sub is not None else ''
        sup_text = process_children(sup) if sup is not None else ''
        return f'{base_text}_{{{sub_text}}}^{{{sup_text}}}'
    
    # Delimiter (parentheses, brackets): m:d
    if tag == 'd':
        dPr = elem.find('m:dPr', namespaces=NAMESPACES)
        begChr = '('
        endChr = ')'
        if dPr is not None:
            beg = dPr.find('m:begChr', namespaces=NAMESPACES)
            end = dPr.find('m:endChr', namespaces=NAMESPACES)
            if beg is not None and beg.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val'):
                begChr = beg.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val')
            if end is not None and end.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val'):
                endChr = end.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val')
        
        content = ''
        for e in elem.findall('m:e', namespaces=NAMESPACES):
            content += process_children(e)
        
        # Convert special brackets to LaTeX
        if begChr == '{': begChr = '\\{'
        if endChr == '}': endChr = '\\}'
        return f'{begChr}{content}{endChr}'
    
    # N-ary (sum, integral, product): m:nary
    if tag == 'nary':
        naryPr = elem.find('m:naryPr', namespaces=NAMESPACES)
        chr_elem = naryPr.find('m:chr', namespaces=NAMESPACES) if naryPr is not None else None
        chr_val = chr_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/math}val') if chr_elem is not None else '∑'
        
        op_map = {'∑': '\\sum', '∏': '\\prod', '∫': '\\int', '∮': '\\oint'}
        op = op_map.get(chr_val, '\\sum')
        
        sub = elem.find('m:sub', namespaces=NAMESPACES)
        sup = elem.find('m:sup', namespaces=NAMESPACES)
        e = elem.find('m:e', namespaces=NAMESPACES)
        
        sub_text = process_children(sub) if sub is not None else ''
        sup_text = process_children(sup) if sup is not None else ''
        e_text = process_children(e) if e is not None else ''
        
        result = op
        if sub_text: result += f'_{{{sub_text}}}'
        if sup_text: result += f'^{{{sup_text}}}'
        result += f' {e_text}'
        return result
    
    # Function: m:func
    if tag == 'func':
        fName = elem.find('m:fName', namespaces=NAMESPACES)
        e = elem.find('m:e', namespaces=NAMESPACES)
        func_name = process_children(fName) if fName is not None else ''
        e_text = process_children(e) if e is not None else ''
        
        # Map common function names
        func_map = {'sin': '\\sin', 'cos': '\\cos', 'tan': '\\tan', 'cot': '\\cot',
                    'log': '\\log', 'ln': '\\ln', 'lim': '\\lim', 'max': '\\max', 'min': '\\min'}
        func_latex = func_map.get(func_name.strip(), f'\\{func_name.strip()}' if func_name.strip() else '')
        return f'{func_latex}{e_text}'
    
    # Bar/Overline: m:bar
    if tag == 'bar':
        e = elem.find('m:e', namespaces=NAMESPACES)
        e_text = process_children(e) if e is not None else ''
        return f'\\overline{{{e_text}}}'
    
    # Text run: m:r containing m:t
    if tag == 'r':
        t = elem.find('m:t', namespaces=NAMESPACES)
        if t is not None and t.text:
            return convert_symbols(t.text)
        return ''
    
    # Default: process all children
    return process_children(elem)


def process_children(elem) -> str:
    """Process all children of an element"""
    if elem is None:
        return ''
    
    result = ''
    # Get text before first child
    if elem.text:
        result += convert_symbols(elem.text)
    
    # Process each child
    for child in elem:
        result += process_element(child)
        # Get text after this child (tail)
        if child.tail:
            result += convert_symbols(child.tail)
    
    return result


def omml_to_latex(omml_xml: str) -> str:
    """
    Convert OMML (Office Math Markup Language) XML to LaTeX string
    
    Args:
        omml_xml: String containing OMML XML content (must have m:oMath as root or contain it)
        
    Returns:
        LaTeX string representation of the math equation, or None if conversion fails
    """
    try:
        # Parse the OMML XML
        root = etree.fromstring(omml_xml.encode('utf-8'))
        
        # If root is already oMath, process it directly
        tag = etree.QName(root.tag).localname if root.tag else ''
        if tag == 'oMath':
            latex = process_children(root)
        else:
            # Find oMath element
            omath = root.find('.//m:oMath', namespaces=NAMESPACES)
            if omath is not None:
                latex = process_children(omath)
            else:
                latex = process_children(root)
        
        # Clean up whitespace
        latex = re.sub(r'\s+', ' ', latex).strip()
        
        return latex if latex else None
        
    except Exception as e:
        print(f"OMML to LaTeX conversion error: {e}")
        return None
