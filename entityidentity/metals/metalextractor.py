"""
Metal text extraction module for entityidentity.

Extracts metal references from unstructured text using heuristics and patterns.
Returns structured hints for the metal_identifier() function.
"""

import re
from typing import List, Dict, Tuple, Optional

# Common element symbols for metals (not exhaustive, focusing on common ones)
ELEMENT_SYMBOLS = {
    # Precious metals
    'Au', 'Ag', 'Pt', 'Pd', 'Rh', 'Ru', 'Ir', 'Os',
    # Base metals
    'Cu', 'Zn', 'Pb', 'Al', 'Ni', 'Sn', 'Fe',
    # Battery metals
    'Li', 'Co', 'Mn', 'C',  # C for graphite
    # Specialty metals
    'W', 'Mo', 'V', 'Ti', 'Ta', 'Nb', 'Zr', 'Hf', 'Re', 'In', 'Ga', 'Ge', 'Te', 'Se', 'Bi', 'Sb', 'Cd',
    # Rare earths
    'La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Y', 'Sc',
    # Others
    'Cr', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'U', 'Th'
}

# Trade specifications and forms
TRADE_SPECS = {
    # Tungsten forms
    r'APT\s*(?:\d+(?:\.\d+)?%?)?': {'hint': 'apt', 'category': 'specialty'},
    r'ammonium\s+paratungstate': {'hint': 'apt', 'category': 'specialty'},

    # Aluminum specs
    r'P1020': {'hint': 'aluminum', 'category': 'base'},
    r'A380': {'hint': 'aluminum', 'category': 'base'},

    # Zinc specs
    r'SHG\s+zinc': {'hint': 'zinc', 'category': 'base'},
    r'special\s+high\s+grade': {'hint': 'zinc', 'category': 'base'},

    # Copper specs
    r'Grade\s+A\s+copper': {'hint': 'copper', 'category': 'base'},
    r'cathode\s+copper': {'hint': 'copper', 'category': 'base'},

    # Battery grade specs
    r'battery[\s-]grade': {'hint': 'battery_grade', 'category': 'battery'},
    r'technical[\s-]grade': {'hint': 'technical_grade', 'category': None},
}

# Chemical forms and compounds
CHEMICAL_FORMS = {
    # Lithium compounds
    r'lithium\s+carbonate': {'name': 'lithium carbonate', 'category': 'battery'},
    r'Li2CO3': {'name': 'lithium carbonate', 'category': 'battery'},
    r'lithium\s+hydroxide': {'name': 'lithium hydroxide', 'category': 'battery'},
    r'LiOH': {'name': 'lithium hydroxide', 'category': 'battery'},

    # Ferroalloys
    r'ferro[\s-]?chrome': {'name': 'ferrochrome', 'category': 'ferroalloy'},
    r'ferro[\s-]?chromium': {'name': 'ferrochrome', 'category': 'ferroalloy'},
    r'FeCr': {'name': 'ferrochrome', 'category': 'ferroalloy'},
    r'ferro[\s-]?manganese': {'name': 'ferromanganese', 'category': 'ferroalloy'},
    r'FeMn': {'name': 'ferromanganese', 'category': 'ferroalloy'},
    r'ferro[\s-]?vanadium': {'name': 'ferrovanadium', 'category': 'ferroalloy'},
    r'FeV': {'name': 'ferrovanadium', 'category': 'ferroalloy'},
    r'ferro[\s-]?tungsten': {'name': 'ferrotungsten', 'category': 'ferroalloy'},
    r'FeW': {'name': 'ferrotungsten', 'category': 'ferroalloy'},
    r'ferro[\s-]?molybdenum': {'name': 'ferromolybdenum', 'category': 'ferroalloy'},
    r'ferro[\s-]?moly': {'name': 'ferromolybdenum', 'category': 'ferroalloy'},
    r'FeMo': {'name': 'ferromolybdenum', 'category': 'ferroalloy'},

    # Sulfates
    r'cobalt\s+sulfate': {'name': 'cobalt sulfate', 'category': 'battery'},
    r'CoSO4': {'name': 'cobalt sulfate', 'category': 'battery'},
    r'nickel\s+sulfate': {'name': 'nickel sulfate', 'category': 'battery'},
    r'NiSO4': {'name': 'nickel sulfate', 'category': 'battery'},

    # REE compounds
    r'NdPr': {'name': 'neodymium-praseodymium', 'category': 'ree'},
    r'Nd-Pr': {'name': 'neodymium-praseodymium', 'category': 'ree'},
    r'didymium': {'name': 'neodymium-praseodymium', 'category': 'ree'},

    # Graphite forms
    r'natural\s+graphite': {'name': 'graphite (natural)', 'category': 'battery'},
    r'synthetic\s+graphite': {'name': 'graphite (synthetic)', 'category': 'battery'},
    r'artificial\s+graphite': {'name': 'graphite (synthetic)', 'category': 'battery'},
    r'spherical\s+graphite': {'name': 'graphite (natural)', 'category': 'battery'},

    # Oxides
    r'alumina': {'name': 'aluminum oxide', 'category': 'base'},
    r'Al2O3': {'name': 'aluminum oxide', 'category': 'base'},
    r'tungsten\s+oxide': {'name': 'tungsten oxide', 'category': 'specialty'},
    r'WO3': {'name': 'tungsten oxide', 'category': 'specialty'},
    r'vanadium\s+pentoxide': {'name': 'vanadium', 'category': 'specialty'},
    r'V2O5': {'name': 'vanadium', 'category': 'specialty'},
}

# Metal name patterns (common names and variations)
METAL_NAMES = {
    # Common variations
    r'wolfram': {'name': 'tungsten', 'category': 'specialty'},
    r'columbium': {'name': 'niobium', 'category': 'specialty'},
    r'quicksilver': {'name': 'mercury', 'category': 'specialty'},

    # Full metal names
    r'platinum': {'name': 'platinum', 'category': 'pgm'},
    r'palladium': {'name': 'palladium', 'category': 'pgm'},
    r'rhodium': {'name': 'rhodium', 'category': 'pgm'},
    r'ruthenium': {'name': 'ruthenium', 'category': 'pgm'},
    r'iridium': {'name': 'iridium', 'category': 'pgm'},
    r'osmium': {'name': 'osmium', 'category': 'pgm'},
    r'gold': {'name': 'gold', 'category': 'precious'},
    r'silver': {'name': 'silver', 'category': 'precious'},
    r'copper': {'name': 'copper', 'category': 'base'},
    r'zinc': {'name': 'zinc', 'category': 'base'},
    r'lead': {'name': 'lead', 'category': 'base'},
    r'aluminum': {'name': 'aluminum', 'category': 'base'},
    r'aluminium': {'name': 'aluminum', 'category': 'base'},
    r'nickel': {'name': 'nickel', 'category': 'battery'},
    r'cobalt': {'name': 'cobalt', 'category': 'battery'},
    r'lithium': {'name': 'lithium', 'category': 'battery'},
    r'graphite': {'name': 'graphite', 'category': 'battery'},
    r'tungsten': {'name': 'tungsten', 'category': 'specialty'},
    r'molybdenum': {'name': 'molybdenum', 'category': 'specialty'},
    r'vanadium': {'name': 'vanadium', 'category': 'specialty'},
    r'tantalum': {'name': 'tantalum', 'category': 'specialty'},
    r'niobium': {'name': 'niobium', 'category': 'specialty'},
    r'rhenium': {'name': 'rhenium', 'category': 'specialty'},
    r'indium': {'name': 'indium', 'category': 'specialty'},
    r'gallium': {'name': 'gallium', 'category': 'specialty'},
    r'germanium': {'name': 'germanium', 'category': 'specialty'},
    r'tellurium': {'name': 'tellurium', 'category': 'specialty'},
    r'selenium': {'name': 'selenium', 'category': 'specialty'},
    r'bismuth': {'name': 'bismuth', 'category': 'specialty'},
    r'antimony': {'name': 'antimony', 'category': 'specialty'},
    r'cadmium': {'name': 'cadmium', 'category': 'specialty'},
    r'chromium': {'name': 'chromium', 'category': 'ferroalloy'},
    r'manganese': {'name': 'manganese', 'category': 'ferroalloy'},
    r'titanium': {'name': 'titanium', 'category': 'specialty'},
    r'zirconium': {'name': 'zirconium', 'category': 'specialty'},
    r'hafnium': {'name': 'hafnium', 'category': 'specialty'},
    r'tin': {'name': 'tin', 'category': 'base'},
    r'iron': {'name': 'iron', 'category': 'base'},
}


def extract_metals_from_text(text: str, cluster_hint: Optional[str] = None) -> List[Dict]:
    """
    Extract metal references from unstructured text.

    Uses heuristics to identify:
    - Element symbols and combinations (Pt/Pd, Ni-Co)
    - Trade specifications (APT 88.5%, P1020, SHG)
    - Chemical forms (lithium carbonate, ferro-chrome)

    Args:
        text: Input text to extract metals from
        cluster_hint: Optional supply chain cluster to prioritize matches

    Returns:
        List of dicts with format:
        [{
            'query': 'pt',           # The matched text
            'span': (10, 12),        # Character position in text
            'hint': 'symbol',        # Type of match (symbol/trade_spec/chemical_form/name)
            'category': 'pgm',       # Optional category hint
            'cluster': None          # Optional cluster hint
        }, ...]
    """
    results = []
    seen_spans = set()  # To avoid duplicate overlapping matches

    # Helper function to add result if not overlapping
    def add_result(query: str, span: Tuple[int, int], hint: str,
                   category: Optional[str] = None, name: Optional[str] = None):
        # Check for overlaps
        for existing_start, existing_end in seen_spans:
            if (span[0] < existing_end and span[1] > existing_start):
                # Overlapping span, skip if the existing one is longer
                if existing_end - existing_start >= span[1] - span[0]:
                    return

        result = {
            'query': name or query,
            'span': span,
            'hint': hint,
        }
        if category:
            result['category'] = category
        if cluster_hint:
            result['cluster'] = cluster_hint

        results.append(result)
        seen_spans.add(span)

    # 1. Extract chemical forms first (most specific, often multi-word)
    for pattern, info in CHEMICAL_FORMS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_result(
                query=match.group(),
                span=match.span(),
                hint='chemical_form',
                category=info.get('category'),
                name=info.get('name')
            )

    # 2. Extract trade specifications
    for pattern, info in TRADE_SPECS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add_result(
                query=match.group(),
                span=match.span(),
                hint='trade_spec',
                category=info.get('category'),
                name=info.get('hint')
            )

    # 3. Extract metal names
    for pattern, info in METAL_NAMES.items():
        # Use word boundaries for metal names
        word_pattern = r'\b' + pattern + r'\b'
        for match in re.finditer(word_pattern, text, re.IGNORECASE):
            add_result(
                query=match.group(),
                span=match.span(),
                hint='name',
                category=info.get('category'),
                name=info.get('name')
            )

    # 4. Extract element symbols and combinations
    # Look for symbols in specific contexts to avoid false positives
    # Context 1: Combinations with / or - (e.g., Pt/Pd, Ni-Co)
    combo_pattern = r'\b(' + '|'.join(ELEMENT_SYMBOLS) + r')([/\-](?:' + '|'.join(ELEMENT_SYMBOLS) + r'))+\b'
    for match in re.finditer(combo_pattern, text):
        add_result(
            query=match.group().lower(),
            span=match.span(),
            hint='symbol_combination',
            category=None  # Mixed, let identifier determine
        )

    # Context 2: Symbols with percentages, parentheses, or after specific words
    # This helps identify actual chemical symbols vs. random capital letters
    context_patterns = [
        # Symbol in parentheses: (Au), (Pt)
        r'\((' + '|'.join(ELEMENT_SYMBOLS) + r')\)',
        # Symbol after colon or equals: : Cu, = Ag
        r'[:=]\s*(' + '|'.join(ELEMENT_SYMBOLS) + r')\b',
        # Symbol with percentage: 99% Cu
        r'\d+(?:\.\d+)?%\s*(' + '|'.join(ELEMENT_SYMBOLS) + r')\b',
        # Symbol after "of" or "for": kg of Cu, price for Au
        r'\b(?:of|for|with|containing)\s+(' + '|'.join(ELEMENT_SYMBOLS) + r')\b',
        # Comma-separated list: Pt, Pd, Rh
        r'(?:^|[,\s])(' + '|'.join(ELEMENT_SYMBOLS) + r')(?=,|\s+(?:and|or)\s+(?:' + '|'.join(ELEMENT_SYMBOLS) + r'))',
        # Symbol at end of sentence or before punctuation
        r'\b(' + '|'.join(ELEMENT_SYMBOLS) + r')(?=[.\s,;:!?\)]|$)',
    ]

    for pattern in context_patterns:
        for match in re.finditer(pattern, text):
            symbol_text = match.group(1) if match.lastindex else match.group()
            symbol_span = (match.start(1) if match.lastindex else match.start(),
                          match.end(1) if match.lastindex else match.end())

            if symbol_text in ELEMENT_SYMBOLS:
                # Avoid duplicates from overlapping patterns
                if any(r['span'] == symbol_span and r['hint'] == 'symbol' for r in results):
                    continue

                # Try to determine category based on symbol
                category = None
                if symbol_text in ['Au', 'Ag']:
                    category = 'precious'
                elif symbol_text in ['Pt', 'Pd', 'Rh', 'Ru', 'Ir', 'Os']:
                    category = 'pgm'
                elif symbol_text in ['Cu', 'Zn', 'Pb', 'Al', 'Ni', 'Sn', 'Fe']:
                    category = 'base'
                elif symbol_text in ['Li', 'Co', 'Mn', 'C']:
                    category = 'battery'
                elif symbol_text in ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Y', 'Sc']:
                    category = 'ree'
                else:
                    category = 'specialty'

                add_result(
                    query=symbol_text.lower(),
                    span=symbol_span,
                    hint='symbol',
                    category=category
                )

    # 5. Look for specific patterns with percentages (e.g., "99.5% copper", "88.5% WO3")
    percent_pattern = r'(\d+(?:\.\d+)?%)\s+(' + '|'.join(ELEMENT_SYMBOLS) + r'|' + '|'.join([k for k in METAL_NAMES.keys()]) + r')'
    for match in re.finditer(percent_pattern, text, re.IGNORECASE):
        metal_text = match.group(2)
        full_text = match.group()
        add_result(
            query=metal_text.lower(),
            span=match.span(),
            hint='purity_spec',
            category=None
        )

    # Sort results by span position
    results.sort(key=lambda x: x['span'][0])

    return results


def extract_metal_pairs(text: str) -> List[Tuple[str, str]]:
    """
    Extract metal pairs or combinations from text (e.g., "Pt/Pd", "Ni-Co").

    Args:
        text: Input text

    Returns:
        List of tuples of metal pairs
    """
    pairs = []

    # Pattern for element combinations
    pair_pattern = r'\b(' + '|'.join(ELEMENT_SYMBOLS) + r')[/\-](' + '|'.join(ELEMENT_SYMBOLS) + r')\b'

    for match in re.finditer(pair_pattern, text):
        metal1 = match.group(1).lower()
        metal2 = match.group(2).lower()
        pairs.append((metal1, metal2))

    return pairs


def categorize_metal_text(text: str) -> Optional[str]:
    """
    Try to categorize a piece of text by metal category.

    Args:
        text: Input text

    Returns:
        Category string or None
    """
    text_lower = text.lower()

    # Check for category keywords
    if any(word in text_lower for word in ['battery', 'lithium-ion', 'ev', 'cathode', 'anode']):
        return 'battery'
    elif any(word in text_lower for word in ['pgm', 'platinum group', 'autocatalyst']):
        return 'pgm'
    elif any(word in text_lower for word in ['precious', 'bullion', 'jewelry']):
        return 'precious'
    elif any(word in text_lower for word in ['steel', 'ferroalloy', 'ferro-']):
        return 'ferroalloy'
    elif any(word in text_lower for word in ['rare earth', 'ree', 'magnet', 'lanthanide']):
        return 'ree'
    elif any(word in text_lower for word in ['base metal', 'lme', 'concentrate']):
        return 'base'
    elif any(word in text_lower for word in ['specialty', 'minor metal', 'technology metal']):
        return 'specialty'

    return None