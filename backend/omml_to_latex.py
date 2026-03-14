"""
OMML (Office Math Markup Language) to LaTeX converter.
This module provides the logic to transform mathematical equations found in
Word documents (stored as OMML XML) into LaTeX strings that can be rendered
by web technologies like MathJax or KaTeX.
"""

import re
import logging
from lxml import etree

# -- 1. Configuration --
# The namespace for Microsoft's mathematical markup language.
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NSMAP = {"m": OMML_NS}

# -- 1.1 Module-Level Constants (Performance: initialized once at import) --
# Moving these dicts out of functions avoids re-creating them on every call.

MATH_CHAR_MAP = {
    # ── Basic Arithmetic & General ──
    "−": "-",  # U+2212 MINUS SIGN
    "×": r"\times ",  # U+00D7
    "÷": r"\div ",  # U+00F7
    "±": r"\pm ",  # U+00B1
    "∓": r"\mp ",  # U+2213
    "⁄": "/",  # U+2044 FRACTION SLASH
    "∕": "/",  # U+2215 DIVISION SLASH
    "·": r"\cdot ",  # U+00B7 MIDDLE DOT
    "°": r"^{\circ}",  # U+00B0 DEGREE SIGN
    "‰": r"\text{\textperthousand}",  # U+2030
    # ── Greek Lowercase ──
    "α": r"\alpha ",
    "β": r"\beta ",
    "γ": r"\gamma ",
    "δ": r"\delta ",
    "ε": r"\varepsilon ",
    "ζ": r"\zeta ",
    "η": r"\eta ",
    "θ": r"\theta ",
    "ι": r"\iota ",
    "κ": r"\kappa ",
    "λ": r"\lambda ",
    "μ": r"\mu ",
    "ν": r"\nu ",
    "ξ": r"\xi ",
    "ο": "o",
    "π": r"\pi ",
    "ρ": r"\rho ",
    "σ": r"\sigma ",
    "ς": r"\varsigma ",  # U+03C2 FINAL SIGMA
    "τ": r"\tau ",
    "υ": r"\upsilon ",
    "φ": r"\varphi ",
    "χ": r"\chi ",
    "ψ": r"\psi ",
    "ω": r"\omega ",
    # ── Greek Uppercase ──
    "Α": "A",
    "Β": "B",
    "Γ": r"\Gamma ",
    "Δ": r"\Delta ",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Θ": r"\Theta ",
    "Ι": "I",
    "Κ": "K",
    "Λ": r"\Lambda ",
    "Μ": "M",
    "Ν": "N",
    "Ξ": r"\Xi ",
    "Ο": "O",
    "Π": r"\Pi ",
    "Ρ": "P",
    "Σ": r"\Sigma ",
    "Τ": "T",
    "Υ": r"\Upsilon ",
    "Φ": r"\Phi ",
    "Χ": "X",
    "Ψ": r"\Psi ",
    "Ω": r"\Omega ",
    # ── Greek Variant Forms ──
    "ϵ": r"\epsilon ",  # U+03F5
    "ϕ": r"\phi ",  # U+03D5
    "ϑ": r"\vartheta ",  # U+03D1
    "ϱ": r"\varrho ",  # U+03F1
    "ϖ": r"\varpi ",  # U+03D6
    "ϰ": r"\varkappa ",  # U+03F0
    "Ϝ": r"\digamma ",  # U+03DC
    "ϝ": r"\digamma ",  # U+03DD
    # ── Letterlike Symbols (U+2100–U+214F) ──
    "ℂ": r"\mathbb{C}",  # U+2102
    "ℍ": r"\mathbb{H}",  # U+210D
    "ℕ": r"\mathbb{N}",  # U+2115
    "ℙ": r"\mathbb{P}",  # U+2119
    "ℚ": r"\mathbb{Q}",  # U+211A
    "ℝ": r"\mathbb{R}",  # U+211D
    "ℤ": r"\mathbb{Z}",  # U+2124
    "ℏ": r"\hbar ",  # U+210F
    "ℓ": r"\ell ",  # U+2113
    "℘": r"\wp ",  # U+2118
    "ℑ": r"\Im ",  # U+2111
    "ℜ": r"\Re ",  # U+211C
    "ℵ": r"\aleph ",  # U+2135
    "ℶ": r"\beth ",  # U+2136
    "ℷ": r"\gimel ",  # U+2137
    "ℸ": r"\daleth ",  # U+2138
    "℧": r"\mho ",  # U+2127
    "Å": r"\text{\AA}",  # U+212B ANGSTROM
    "℃": r"^{\circ}\text{C}",  # U+2103
    "℉": r"^{\circ}\text{F}",  # U+2109
    "№": r"\text{No.}",  # U+2116
    # ── Arrows (U+2190–U+21FF) ──
    "←": r"\leftarrow ",
    "↑": r"\uparrow ",
    "→": r"\rightarrow ",
    "↓": r"\downarrow ",
    "↔": r"\leftrightarrow ",
    "↕": r"\updownarrow ",
    "↖": r"\nwarrow ",
    "↗": r"\nearrow ",
    "↘": r"\searrow ",
    "↙": r"\swarrow ",
    "↦": r"\mapsto ",
    "↩": r"\hookleftarrow ",
    "↪": r"\hookrightarrow ",
    "↼": r"\leftharpoonup ",
    "↽": r"\leftharpoondown ",
    "⇀": r"\rightharpoonup ",
    "⇁": r"\rightharpoondown ",
    "⇌": r"\rightleftharpoons ",
    "⇒": r"\Rightarrow ",
    "⇐": r"\Leftarrow ",
    "⇑": r"\Uparrow ",
    "⇓": r"\Downarrow ",
    "⇔": r"\Leftrightarrow ",
    "⇕": r"\Updownarrow ",
    "⟵": r"\longleftarrow ",  # U+27F5
    "⟶": r"\longrightarrow ",  # U+27F6
    "⟷": r"\longleftrightarrow ",  # U+27F7
    "⟸": r"\Longleftarrow ",  # U+27F8
    "⟹": r"\Longrightarrow ",  # U+27F9
    "⟺": r"\Longleftrightarrow ",  # U+27FA
    "⟼": r"\longmapsto ",  # U+27FC
    # ── Mathematical Operators (U+2200–U+22FF) ──
    # Logic & Quantifiers
    "∀": r"\forall ",
    "∁": r"\complement ",  # U+2201
    "∂": r"\partial ",
    "∃": r"\exists ",
    "∄": r"\nexists ",
    "∅": r"\emptyset ",
    "∇": r"\nabla ",
    # Set Membership
    "∈": r"\in ",
    "∉": r"\notin ",
    "∋": r"\ni ",  # U+220B CONTAINS AS MEMBER
    "∌": r"\not\ni ",  # U+220C
    # N-ary & Big Operators (as inline text)
    "∏": r"\prod ",
    "∐": r"\coprod ",  # U+2210
    "∑": r"\sum ",
    # Arithmetic & Algebra
    "∗": r"\ast ",  # U+2217
    "∘": r"\circ ",  # U+2218
    "√": r"\sqrt ",
    "∛": r"\sqrt[3] ",  # U+221B CUBE ROOT
    "∜": r"\sqrt[4] ",  # U+221C FOURTH ROOT
    "∝": r"\propto ",  # U+221D
    "∞": r"\infty ",
    # Geometry & Angles
    "∟": r"\measuredangle ",  # U+221F RIGHT ANGLE
    "∠": r"\angle ",  # U+2220
    "∡": r"\measuredangle ",  # U+2221
    "∢": r"\sphericalangle ",  # U+2222
    # Parallel & Perpendicular
    "∥": r"\parallel ",  # U+2225
    "∦": r"\nparallel ",  # U+2226
    "⊥": r"\perp ",  # U+22A5
    # Logical Operators
    "∧": r"\wedge ",  # U+2227
    "∨": r"\vee ",  # U+2228
    "¬": r"\neg ",  # U+00AC
    # Integrals
    "∫": r"\int ",
    "∬": r"\iint ",  # U+222C
    "∭": r"\iiint ",  # U+222D
    "∮": r"\oint ",  # U+222E
    "∯": r"\oiint ",  # U+222F
    "∰": r"\oiiint ",  # U+2230
    # Operators
    "∴": r"\therefore ",  # U+2234
    "∵": r"\because ",  # U+2235
    "∶": ":",  # U+2236 RATIO
    "∷": r"\dblcolon ",  # U+2237 PROPORTION
    "∸": r"\dotminus ",  # U+2238
    # Tilde & Similarity
    "∼": r"\sim ",  # U+223C
    "∽": r"\backsim ",  # U+223D
    "≃": r"\simeq ",  # U+2243
    "≅": r"\cong ",  # U+2245
    "≆": r"\ncong ",  # U+2246
    "≇": r"\ncong ",  # U+2247
    "≈": r"\approx ",
    "≉": r"\not\approx ",  # U+2249
    # Equality & Equivalence
    "≐": r"\doteq ",  # U+2250
    "≑": r"\doteqdot ",  # U+2251
    "≒": r"\fallingdotseq ",  # U+2252
    "≓": r"\risingdotseq ",  # U+2253
    "≔": r":=",  # U+2254 COLON EQUALS
    "≕": r"=:",  # U+2255 EQUALS COLON
    "≜": r"\triangleq ",  # U+225C
    "≝": r"\overset{\text{def}}{=}",  # U+225D
    "≠": r"\neq ",
    "≡": r"\equiv ",  # U+2261
    "≢": r"\not\equiv ",  # U+2262
    # Ordering & Inequalities
    "≤": r"\leq ",
    "≥": r"\geq ",
    "≦": r"\leqq ",  # U+2266
    "≧": r"\geqq ",  # U+2267
    "≨": r"\lneqq ",  # U+2268
    "≩": r"\gneqq ",  # U+2269
    "≪": r"\ll ",  # U+226A
    "≫": r"\gg ",  # U+226B
    "≮": r"\nless ",  # U+226E
    "≯": r"\ngtr ",  # U+226F
    "≰": r"\nleq ",  # U+2270
    "≱": r"\ngeq ",  # U+2271
    "≲": r"\lesssim ",  # U+2272
    "≳": r"\gtrsim ",  # U+2273
    # Precedes & Succeeds
    "≺": r"\prec ",  # U+227A
    "≻": r"\succ ",  # U+227B
    "≼": r"\preccurlyeq ",  # U+227C
    "≽": r"\succcurlyeq ",  # U+227D
    "≾": r"\precsim ",  # U+227E
    "≿": r"\succsim ",  # U+227F
    "⊀": r"\nprec ",  # U+2280
    "⊁": r"\nsucc ",  # U+2281
    # Subsets & Supersets
    "⊂": r"\subset ",
    "⊃": r"\supset ",
    "⊄": r"\not\subset ",  # U+2284
    "⊅": r"\not\supset ",  # U+2285
    "⊆": r"\subseteq ",
    "⊇": r"\supseteq ",
    "⊈": r"\nsubseteq ",  # U+2288
    "⊉": r"\nsupseteq ",  # U+2289
    "⊊": r"\subsetneq ",  # U+228A
    "⊋": r"\supsetneq ",  # U+228B
    "⊏": r"\sqsubset ",  # U+228F
    "⊐": r"\sqsupset ",  # U+2290
    "⊑": r"\sqsubseteq ",  # U+2291
    "⊒": r"\sqsupseteq ",  # U+2292
    # Set Operations
    "∪": r"\cup ",
    "∩": r"\cap ",
    "⊎": r"\uplus ",  # U+228E
    "⊓": r"\sqcap ",  # U+2293
    "⊔": r"\sqcup ",  # U+2294
    # Lattice & Turnstile
    "⊕": r"\oplus ",  # U+2295
    "⊖": r"\ominus ",  # U+2296
    "⊗": r"\otimes ",  # U+2297
    "⊘": r"\oslash ",  # U+2298
    "⊙": r"\odot ",  # U+2299
    "⊚": r"\circledcirc ",  # U+229A
    "⊛": r"\circledast ",  # U+229B
    "⊝": r"\circleddash ",  # U+229D
    "⊞": r"\boxplus ",  # U+229E
    "⊟": r"\boxminus ",  # U+229F
    "⊠": r"\boxtimes ",  # U+22A0
    "⊡": r"\boxdot ",  # U+22A1
    "⊢": r"\vdash ",  # U+22A2
    "⊣": r"\dashv ",  # U+22A3
    "⊤": r"\top ",  # U+22A4
    "⊧": r"\models ",  # U+22A7
    "⊨": r"\models ",  # U+22A8
    "⊩": r"\Vdash ",  # U+22A9
    "⊬": r"\nvdash ",  # U+22AC
    "⊭": r"\nvDash ",  # U+22AD
    "⊮": r"\nVdash ",  # U+22AE
    "⊯": r"\nVDash ",  # U+22AF
    # Miscellaneous Operators
    "⋅": r"\cdot ",
    "⋆": r"\star ",  # U+22C6
    "⋇": r"\divideontimes ",  # U+22C7
    "⋈": r"\bowtie ",  # U+22C8
    "⋉": r"\ltimes ",  # U+22C9
    "⋊": r"\rtimes ",  # U+22CA
    "⋋": r"\leftthreetimes ",  # U+22CB
    "⋌": r"\rightthreetimes ",  # U+22CC
    "⋍": r"\backsimeq ",  # U+22CD
    "⋎": r"\curlyvee ",  # U+22CE
    "⋏": r"\curlywedge ",  # U+22CF
    # Diagonal Relations
    "⋐": r"\Subset ",  # U+22D0
    "⋑": r"\Supset ",  # U+22D1
    "⋒": r"\Cap ",  # U+22D2
    "⋓": r"\Cup ",  # U+22D3
    "⋔": r"\pitchfork ",  # U+22D4
    "⋖": r"\lessdot ",  # U+22D6
    "⋗": r"\gtrdot ",  # U+22D7
    "⋘": r"\lll ",  # U+22D8
    "⋙": r"\ggg ",  # U+22D9
    "⋚": r"\lesseqgtr ",  # U+22DA
    "⋛": r"\gtreqless ",  # U+22DB
    "⋜": r"\eqslantless ",  # U+22DC
    "⋝": r"\eqslantgtr ",  # U+22DD
    "⋞": r"\curlyeqprec ",  # U+22DE
    "⋟": r"\curlyeqsucc ",  # U+22DF
    # N-ary Operators
    "⋀": r"\bigwedge ",  # U+22C0
    "⋁": r"\bigvee ",  # U+22C1
    "⋂": r"\bigcap ",  # U+22C2
    "⋃": r"\bigcup ",  # U+22C3
    # Dots
    "…": r"\ldots ",
    "⋯": r"\cdots ",
    "⋮": r"\vdots ",
    "⋱": r"\ddots ",
    "⋰": r"\iddots ",  # U+22F0 UP RIGHT DIAGONAL ELLIPSIS
    # Divisibility
    "∣": r"\mid ",  # U+2223
    "∤": r"\nmid ",  # U+2224
    # Wreath & Other
    "≀": r"\wr ",  # U+2240 WREATH PRODUCT
    # ── Supplemental Math Operators (U+2A00–U+2AFF) ──
    "⨀": r"\bigodot ",  # U+2A00
    "⨁": r"\bigoplus ",  # U+2A01
    "⨂": r"\bigotimes ",  # U+2A02
    "⨄": r"\biguplus ",  # U+2A04
    "⨆": r"\bigsqcup ",  # U+2A06
    "⨉": r"\bigtimes ",  # U+2A09
    # ── Miscellaneous Technical (U+2300–U+23FF) ──
    "⌈": r"\lceil ",  # U+2308
    "⌉": r"\rceil ",  # U+2309
    "⌊": r"\lfloor ",  # U+230A
    "⌋": r"\rfloor ",  # U+230B
    "⌢": r"\frown ",  # U+2322
    "⌣": r"\smile ",  # U+2323
    "⌐": r"\lnot ",  # U+2310
    "⏞": r"\overbrace ",  # U+23DE
    "⏟": r"\underbrace ",  # U+23DF
    "⎰": r"\lmoustache ",  # U+23B0
    "⎱": r"\rmoustache ",  # U+23B1
    # ── Miscellaneous Math Symbols-A (U+27C0–U+27EF) ──
    "⟨": r"\langle ",  # U+27E8
    "⟩": r"\rangle ",  # U+27E9
    "⟪": r"\lAngle ",  # U+27EA
    "⟫": r"\rAngle ",  # U+27EB
    "⟦": r"\llbracket ",  # U+27E6
    "⟧": r"\rrbracket ",  # U+27E7
    # ── Miscellaneous Math Symbols-B (U+2980–U+29FF) ──
    "⦃": r"\lBrace ",  # U+2983
    "⦄": r"\rBrace ",  # U+2984
    "‖": r"\| ",  # U+2016 DOUBLE VERTICAL LINE
    # ── Geometric Shapes (U+25A0–U+25FF) ──
    "△": r"\triangle ",  # U+25B3
    "▲": r"\blacktriangle ",  # U+25B2
    "▷": r"\triangleright ",  # U+25B7
    "▽": r"\triangledown ",  # U+25BD
    "▼": r"\blacktriangledown ",  # U+25BC
    "◁": r"\triangleleft ",  # U+25C1
    "◇": r"\diamond ",  # U+25C7
    "◆": r"\blacklozenge ",  # U+25C6
    "○": r"\bigcirc ",  # U+25CB
    "●": r"\bullet ",  # U+25CF
    "□": r"\square ",  # U+25A1
    "■": r"\blacksquare ",  # U+25A0
    "◊": r"\lozenge ",  # U+25CA
    "★": r"\bigstar ",  # U+2605
    "☆": r"\star ",  # U+2606
    # ── Primes & Marks ──
    "′": "'",  # U+2032
    "″": "''",  # U+2033
    "‴": "'''",  # U+2034
    "⁗": "''''",  # U+2057
    # ── General Punctuation ──
    "–": "-",  # U+2013 EN DASH
    "—": "-",  # U+2014 EM DASH
    "‐": "-",  # U+2010 HYPHEN
    "‑": "-",  # U+2011 NON-BREAKING HYPHEN
    "†": r"\dagger ",  # U+2020
    "‡": r"\ddagger ",  # U+2021
    "•": r"\bullet ",  # U+2022
    "‾": r"\overline{\phantom{a}}",  # U+203E OVERLINE
    # ── Superscripts & Subscripts (U+2070–U+209F) ──
    "⁰": r"^{0}",
    "¹": r"^{1}",
    "²": r"^{2}",
    "³": r"^{3}",
    "⁴": r"^{4}",
    "⁵": r"^{5}",
    "⁶": r"^{6}",
    "⁷": r"^{7}",
    "⁸": r"^{8}",
    "⁹": r"^{9}",
    "⁺": r"^{+}",
    "⁻": r"^{-}",
    "⁼": r"^{=}",
    "⁽": r"^{(}",
    "⁾": r"^{)}",
    "ⁿ": r"^{n}",
    "ⁱ": r"^{i}",
    "₀": r"_{0}",
    "₁": r"_{1}",
    "₂": r"_{2}",
    "₃": r"_{3}",
    "₄": r"_{4}",
    "₅": r"_{5}",
    "₆": r"_{6}",
    "₇": r"_{7}",
    "₈": r"_{8}",
    "₉": r"_{9}",
    "₊": r"_{+}",
    "₋": r"_{-}",
    "₌": r"_{=}",
    "₍": r"_{(}",
    "₎": r"_{)}",
    # ── Miscellaneous Symbols ──
    "♠": r"\spadesuit ",  # U+2660
    "♣": r"\clubsuit ",  # U+2663
    "♥": r"\heartsuit ",  # U+2665
    "♦": r"\diamondsuit ",  # U+2666
    "♭": r"\flat ",  # U+266D
    "♮": r"\natural ",  # U+266E
    "♯": r"\sharp ",  # U+266F
    "✓": r"\checkmark ",  # U+2713
    "✗": r"\times ",  # U+2717
    "∎": r"\blacksquare ",  # U+220E END OF PROOF
    # ── CJK-style angle brackets (for compatibility) ──
    "〈": r"\langle ",  # U+3008
    "〉": r"\rangle ",  # U+3009
    }



ACCENT_MAP = {
    "^": r"\hat",
    "̂": r"\hat",  # U+0302 COMBINING CIRCUMFLEX
    "~": r"\tilde",
    "̃": r"\tilde",  # U+0303 COMBINING TILDE
    "¯": r"\bar",
    "̄": r"\bar",  # U+0304 COMBINING MACRON
    "→": r"\vec",
    "⃗": r"\vec",  # U+20D7 COMBINING RIGHT ARROW
    ".": r"\dot",
    "̇": r"\dot",  # U+0307 COMBINING DOT ABOVE
    "..": r"\ddot",
    "̈": r"\ddot",  # U+0308 COMBINING DIAERESIS
    "˘": r"\breve",
    "̆": r"\breve",  # U+0306 COMBINING BREVE
    "ˇ": r"\check",
    "̌": r"\check",  # U+030C COMBINING CARON
    "˚": r"\mathring",  # U+02DA RING ABOVE
    "̊": r"\mathring",  # U+030A COMBINING RING ABOVE
    "́": r"\acute",  # U+0301 COMBINING ACUTE
    "´": r"\acute",  # U+00B4 ACUTE ACCENT
    "̀": r"\grave",  # U+0300 COMBINING GRAVE
    "`": r"\grave",
    "⃛": r"\dddot",  # U+20DB COMBINING THREE DOTS ABOVE
    "⃜": r"\ddddot",  # U+20DC COMBINING FOUR DOTS ABOVE
    "‾": r"\overline",  # U+203E OVERLINE
    "⃐": r"\overleftarrow",  # U+20D0 COMBINING LEFT ARROW
    "⃑": r"\overrightarrow",  # U+20D1 COMBINING RIGHT ARROW
    }

BEGIN_DELIM_MAP = {
    "(": r"\left(",
    "[": r"\left[",
    "{": r"\left\{",
    "|": r"\left|",
    "‖": r"\left\|",  # U+2016 DOUBLE VERTICAL LINE
    "∥": r"\left\|",  # U+2225 PARALLEL TO (as double bar)
    "⌈": r"\left\lceil",
    "⌊": r"\left\lfloor",
    "〈": r"\left\langle",  # U+3008 CJK
    "⟨": r"\left\langle",  # U+27E8 MATHEMATICAL
    "⟪": r"\left\langle\langle",  # U+27EA DOUBLE ANGLE
    "⟦": r"\left[\![",  # U+27E6 DOUBLE BRACKET
    "⦃": r"\left\{",  # U+2983 LEFT CURLY BRACKET
    "": "",
}

END_DELIM_MAP = {
    ")": r"\right)",
    "]": r"\right]",
    "}": r"\right\}",
    "|": r"\right|",
    "‖": r"\right\|",  # U+2016 DOUBLE VERTICAL LINE
    "∥": r"\right\|",  # U+2225 PARALLEL TO (as double bar)
    "⌉": r"\right\rceil",
    "⌋": r"\right\rfloor",
    "〉": r"\right\rangle",  # U+3009 CJK
    "⟩": r"\right\rangle",  # U+27E9 MATHEMATICAL
    "⟫": r"\right\rangle\rangle",  # U+27EB DOUBLE ANGLE
    "⟧": r"\right]\!]",  # U+27E7 DOUBLE BRACKET
    "⦄": r"\right\}",  # U+2984 RIGHT CURLY BRACKET
    "": "",
}

NARY_MAP = {
    "∑": r"\sum",
    "∏": r"\prod",
    "∐": r"\coprod",
    "∫": r"\int",
    "∬": r"\iint",
    "∭": r"\iiint",
    "∮": r"\oint",
    "∯": r"\oiint",
    "∰": r"\oiiint",
    "⋃": r"\bigcup",
    "⋂": r"\bigcap",
    "⋁": r"\bigvee",
    "⋀": r"\bigwedge",
    "⨀": r"\bigodot",
    "⨁": r"\bigoplus",
    "⨂": r"\bigotimes",
    "⨄": r"\biguplus",
    "⨆": r"\bigsqcup",
}

FUNC_MAP = {
    "sin": r"\sin",
    "cos": r"\cos",
    "tan": r"\tan",
    "cot": r"\cot",
    "sec": r"\sec",
    "csc": r"\csc",
    "arcsin": r"\arcsin",
    "arccos": r"\arccos",
    "arctan": r"\arctan",
    "sinh": r"\sinh",
    "cosh": r"\cosh",
    "tanh": r"\tanh",
    "log": r"\log",
    "ln": r"\ln",
    "lg": r"\lg",
    "exp": r"\exp",
    "lim": r"\lim",
    "min": r"\min",
    "max": r"\max",
    "inf": r"\inf",
    "sup": r"\sup",
    "det": r"\det",
    "dim": r"\dim",
    "ker": r"\ker",
    "gcd": r"\gcd",
    "lcm": r"\text{lcm}",
    "mod": r"\mod",
}




def omml_to_latex(omml_xml: str) -> str:
    """
    Main entry point to convert an OMML XML snippet into a LaTeX string.
    Steps:
    1. Parse the XML string into an element tree.
    2. Recursively traverse the tree and convert each element.
    3. Perform post-processing for clean LaTeX output.
    """
    try:
        if isinstance(omml_xml, str):
            root = etree.fromstring(omml_xml.encode("utf-8"))
        else:
            root = etree.fromstring(omml_xml)

        # Traverse and convert.
        latex = _convert_element(root)

        # Clean up unnecessary spaces or empty braces.
        latex = _cleanup_latex(latex)

        return latex
    except Exception as e:
        logging.getLogger("omml_to_latex").error(
            f"Conversion error: {e}", exc_info=True
        )
        return None


def _get_local_name(element):
    """Utility to strip the '{...}' namespace prefix from an XML tag name."""
    if element.tag.startswith("{"):
        return element.tag.split("}")[1]
    return element.tag


def _convert_element(element) -> str:
    """
    The core recursive function that maps OMML XML tags to LaTeX commands.
    It identifies the type of mathematical construct (fraction, root, etc.)
    and calls the appropriate helper function.
    """
    tag = _get_local_name(element)

    # 1. Containers
    if tag in ("oMath", "oMathPara"):
        return "".join(_convert_element(child) for child in element)

    # 2. Basic Text Run
    elif tag == "r":
        return _convert_run(element)

    # 3. Fractions (e.g., a/b -> \frac{a}{b})
    elif tag == "f":
        return _convert_fraction(element)

    # 4. Radicals (e.g., √x -> \sqrt{x})
    elif tag == "rad":
        return _convert_radical(element)

    # 5. Superscripts and Subscripts
    elif tag == "sSup":
        return _convert_superscript(element)
    elif tag == "sSub":
        return _convert_subscript(element)
    elif tag == "sSubSup":
        return _convert_subsup(element)

    # 6. Delimiters (Parentheses, brackets)
    elif tag == "d":
        return _convert_delimiter(element)

    # 7. Operators (Sum, Integral, etc.)
    elif tag == "nary":
        return _convert_nary(element)

    # 8. Matrices
    elif tag == "m":
        return _convert_matrix(element)

    # 9. Limits (Upper and Lower)
    elif tag == "limLow":
        return _convert_lim_low(element)
    elif tag == "limUpp":
        return _convert_lim_upp(element)

    # 10. Trigonometric and other functions
    elif tag == "func":
        return _convert_function(element)

    # 11. Accents (Hats, bars, vectors)
    elif tag == "acc":
        return _convert_accent(element)
    elif tag == "bar":
        return _convert_bar(element)

    # 12. Grouping (Braces under/over text)
    elif tag == "groupChr":
        return _convert_group_chr(element)

    # 13. Box (unpacks boxed content)
    elif tag == "box":
        return _convert_box(element)

    # 14. Equation Array (multiline aligned equations)
    elif tag == "eqArr":
        return _convert_eq_array(element)

    # 15. Border Box (equations inside a visual box)
    elif tag == "borderBox":
        return _convert_border_box(element)

    # 16. Pre-subscript/superscript
    elif tag == "sPre":
        return _convert_pre_sub_sup(element)

    # 17. Phantom (invisible placeholder for alignment)
    elif tag == "phant":
        return _convert_phantom(element)

    # Handle nested content elements (numerator, denominator, base, etc.)
    elif tag in ("e", "num", "den", "deg", "sub", "sup", "lim", "fName"):
        return "".join(_convert_element(child) for child in element)

    # Leaf Text nodes
    elif tag == "t":
        return _convert_text(element)

    # Skip styling/property tags
    elif tag in (
        "rPr",
        "ctrlPr",
        "argPr",
        "fPr",
        "radPr",
        "sSupPr",
        "sSubPr",
        "sSubSupPr",
        "dPr",
        "naryPr",
        "mPr",
        "limLowPr",
        "limUppPr",
        "funcPr",
        "accPr",
        "barPr",
        "groupChrPr",
        "boxPr",
        "eqArrPr",
        "borderBoxPr",
        "sPrePr",
        "phantPr",
        "mcs",
        "mr",
    ):
        return ""

    # Recurse for unknown elements.
    else:
        return "".join(_convert_element(child) for child in element)


def _convert_run(element) -> str:
    """Processes a mathematical 'Run' element containing text."""
    result = []
    for child in element:
        tag = _get_local_name(child)
        if tag == "t":
            result.append(_convert_text(child))
    return "".join(result)


def _convert_text(element) -> str:
    """
    Converts raw text within a math zone.
    Uses the module-level MATH_CHAR_MAP constant for performance
    (initialized once at import, not on every call).
    """
    text = element.text or ""


    for char, latex in MATH_CHAR_MAP.items():
        text = text.replace(char, latex)

    return text


def _convert_fraction(element) -> str:
    """Transfers OMML numerator/denominator to \\frac{num}{den}."""
    num = ""
    den = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "num":
            num = "".join(_convert_element(c) for c in child)
        elif tag == "den":
            den = "".join(_convert_element(c) for c in child)
    return r"\frac{" + num + "}{" + den + "}"


def _convert_radical(element) -> str:
    """Transfers roots to \\sqrt{base} or \\sqrt[degree]{base}."""
    degree = ""
    base = ""

    # Check if the degree should be hidden (square root).
    rad_pr = element.find("m:radPr", namespaces=NSMAP)
    deg_hide = False
    if rad_pr is not None:
        deg_hide_elem = rad_pr.find("m:degHide", namespaces=NSMAP)
        if deg_hide_elem is not None:
            val = deg_hide_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "0"
            )
            deg_hide = val in ("1", "true", "on")

    for child in element:
        tag = _get_local_name(child)
        if tag == "deg":
            degree = "".join(_convert_element(c) for c in child).strip()
        elif tag == "e":
            base = "".join(_convert_element(c) for c in child)

    if deg_hide or not degree or degree == "2":
        return r"\sqrt{" + base + "}"
    else:
        return r"\sqrt[" + degree + "]{" + base + "}"


def _convert_superscript(element) -> str:
    """Handles superscripts (powers)."""
    base = ""
    sup = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)
        elif tag == "sup":
            sup = "".join(_convert_element(c) for c in child)
    return base + "^{" + sup + "}"


def _convert_subscript(element) -> str:
    """Handles subscripts."""
    base = ""
    sub = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)
        elif tag == "sub":
            sub = "".join(_convert_element(c) for c in child)
    return base + "_{" + sub + "}"


def _convert_subsup(element) -> str:
    """Handles elements with both subscript and superscript (e.g., integral limits)."""
    base = ""
    sub = ""
    sup = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)
        elif tag == "sub":
            sub = "".join(_convert_element(c) for c in child)
        elif tag == "sup":
            sup = "".join(_convert_element(c) for c in child)
    return base + "_{" + sub + "}^{" + sup + "}"


def _convert_delimiter(element) -> str:
    """Handles delimiters like (parentheses) and [brackets] with automatic scaling."""
    beg_chr = "("
    end_chr = ")"

    # Extract delimiter characters from properties.
    d_pr = element.find("m:dPr", namespaces=NSMAP)
    if d_pr is not None:
        beg_chr_elem = d_pr.find("m:begChr", namespaces=NSMAP)
        end_chr_elem = d_pr.find("m:endChr", namespaces=NSMAP)
        if beg_chr_elem is not None:
            beg_chr = beg_chr_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "("
            )
        if end_chr_elem is not None:
            end_chr = end_chr_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", ")"
            )



    left = BEGIN_DELIM_MAP.get(beg_chr, r"\left" + beg_chr)
    right = END_DELIM_MAP.get(end_chr, r"\right" + end_chr)

    content_parts = []
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            content_parts.append("".join(_convert_element(c) for c in child))

    content = (
        ",".join(content_parts)
        if len(content_parts) > 1
        else (content_parts[0] if content_parts else "")
    )

    return left + content + right


def _convert_nary(element) -> str:
    """Handles N-ary operators like Sum (Σ) and Integral (∫)."""
    operator = r"\int "
    sub = ""
    sup = ""
    base = ""

    nary_pr = element.find("m:naryPr", namespaces=NSMAP)
    if nary_pr is not None:
        chr_elem = nary_pr.find("m:chr", namespaces=NSMAP)
        if chr_elem is not None:
            char = chr_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "∫"
            )

            operator = NARY_MAP.get(char, r"\int")

    for child in element:
        tag = _get_local_name(child)
        if tag == "sub":
            sub = "".join(_convert_element(c) for c in child)
        elif tag == "sup":
            sup = "".join(_convert_element(c) for c in child)
        elif tag == "e":
            base = "".join(_convert_element(c) for c in child)

    result = operator
    if sub:
        result += "_{" + sub + "}"
    if sup:
        result += "^{" + sup + "}"
    result += " " + base

    return result


def _convert_matrix(element) -> str:
    """Converts a math matrix structure."""
    rows = []
    for child in element:
        tag = _get_local_name(child)
        if tag == "mr":
            cells = []
            for cell in child:
                cell_tag = _get_local_name(cell)
                if cell_tag == "e":
                    cells.append("".join(_convert_element(c) for c in cell))
            rows.append(" & ".join(cells))

    return r"\begin{matrix}" + r" \\ ".join(rows) + r"\end{matrix}"


def _convert_lim_low(element) -> str:
    """Handles lower limits (often used for limits and infimums)."""
    base = ""
    lim = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)
        elif tag == "lim":
            lim = "".join(_convert_element(c) for c in child)

    if base.strip().lower() in ("lim", "liminf", "limsup"):
        return r"\lim_{" + lim + "}"

    return base + "_{" + lim + "}"


def _convert_lim_upp(element) -> str:
    """Handles upper limits."""
    base = ""
    lim = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)
        elif tag == "lim":
            lim = "".join(_convert_element(c) for c in child)

    return base + "^{" + lim + "}"


def _convert_function(element) -> str:
    """Converts common mathematical functions (sin, cos, log, etc.)."""
    fname = ""
    arg = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "fName":
            fname = "".join(_convert_element(c) for c in child).strip()
        elif tag == "e":
            arg = "".join(_convert_element(c) for c in child)

    # Map to standard LaTeX function commands.


    latex_fname = FUNC_MAP.get(fname.lower(), r"\text{" + fname + "}")
    return latex_fname + " " + arg


def _convert_accent(element) -> str:
    """Handles accent symbols (hats, vectors)."""
    char = "^"
    base = ""

    acc_pr = element.find("m:accPr", namespaces=NSMAP)
    if acc_pr is not None:
        chr_elem = acc_pr.find("m:chr", namespaces=NSMAP)
        if chr_elem is not None:
            char = chr_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "^"
            )

    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)



    accent = ACCENT_MAP.get(char, r"\hat")
    return accent + "{" + base + "}"


def _convert_bar(element) -> str:
    """Handles bar accents (overline/underline)."""
    base = ""
    pos = "top"

    bar_pr = element.find("m:barPr", namespaces=NSMAP)
    if bar_pr is not None:
        pos_elem = bar_pr.find("m:pos", namespaces=NSMAP)
        if pos_elem is not None:
            pos = pos_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "top"
            )

    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)

    if pos == "bot":
        return r"\underline{" + base + "}"
    else:
        return r"\overline{" + base + "}"


def _convert_group_chr(element) -> str:
    """Handles grouping marks (underbrace/overbrace)."""
    base = ""
    char = "⏟"
    pos = "bot"

    group_pr = element.find("m:groupChrPr", namespaces=NSMAP)
    if group_pr is not None:
        chr_elem = group_pr.find("m:chr", namespaces=NSMAP)
        pos_elem = group_pr.find("m:pos", namespaces=NSMAP)
        if chr_elem is not None:
            char = chr_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "⏟"
            )
        if pos_elem is not None:
            pos = pos_elem.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/math}val", "bot"
            )

    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)

    if char == "⏞" or pos == "top":
        return r"\overbrace{" + base + "}"
    else:
        return r"\underbrace{" + base + "}"


def _convert_box(element) -> str:
    """Unpacks boxed content."""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            return "".join(_convert_element(c) for c in child)
    return ""


def _convert_eq_array(element) -> str:
    """Handles multiline equations (aligned environment)."""
    rows = []
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            rows.append("".join(_convert_element(c) for c in child))

    return r"\begin{aligned}" + r" \\ ".join(rows) + r"\end{aligned}"


def _convert_border_box(element) -> str:
    """Handles equations inside a visual box."""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            return r"\boxed{" + "".join(_convert_element(c) for c in child) + "}"
    return ""


def _convert_pre_sub_sup(element) -> str:
    """Handles scripts that appear BEFORE the base element."""
    base = ""
    sub = ""
    sup = ""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            base = "".join(_convert_element(c) for c in child)
        elif tag == "sub":
            sub = "".join(_convert_element(c) for c in child)
        elif tag == "sup":
            sup = "".join(_convert_element(c) for c in child)

    return "{}_{" + sub + "}^{" + sup + "}" + base


def _convert_phantom(element) -> str:
    """Handles phantom elements (invisible placeholders for alignment)."""
    for child in element:
        tag = _get_local_name(child)
        if tag == "e":
            content = "".join(_convert_element(c) for c in child)
            return r"\phantom{" + content + "}"
    return ""


def _cleanup_latex(latex: str) -> str:
    """Refines the finalized LaTeX string by removing extra whitespace."""
    if not latex:
        return latex

    latex = re.sub(r"\s+", " ", latex)
    latex = latex.strip()
    latex = re.sub(r"\{\s*\}", "", latex)  # Remove empty braces.
    latex = re.sub(r"  +", " ", latex)
    return latex
