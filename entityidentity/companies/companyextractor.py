"""Text extraction utilities for finding company mentions."""

import re
from typing import List, Optional, Dict, Any

from entityidentity.companies.companyidentity import resolve_company, load_companies


def extract_companies_from_text(
    text: str,
    country_hint: Optional[str] = None,
    min_confidence: float = 0.75,
) -> List[Dict[str, Any]]:
    """Extract company mentions from text and resolve to canonical identifiers.
    
    This function:
    1. Identifies potential company names (capitalized phrases, legal suffixes)
    2. Infers country context from the text if not provided
    3. Attempts to match each candidate to the company database
    4. Returns matches above the confidence threshold
    
    Args:
        text: Text to extract companies from
        country_hint: Optional country code to prioritize (e.g., "US", "GB")
        min_confidence: Minimum match score to include (0.0-1.0, default 0.75)
        
    Returns:
        List of matched company dictionaries
    """
    if not text:
        return []
    
    # Country name to code mapping
    COUNTRY_NAMES = {
        'united states': 'US', 'usa': 'US', 'america': 'US', 'american': 'US',
        'united kingdom': 'GB', 'uk': 'GB', 'britain': 'GB', 'british': 'GB',
        'australia': 'AU', 'australian': 'AU',
        'canada': 'CA', 'canadian': 'CA',
        'germany': 'DE', 'german': 'DE',
        'france': 'FR', 'french': 'FR',
        'japan': 'JP', 'japanese': 'JP',
        'china': 'CN', 'chinese': 'CN',
        'india': 'IN', 'indian': 'IN',
        'brazil': 'BR', 'brazilian': 'BR',
        'south africa': 'ZA',
        'switzerland': 'CH', 'swiss': 'CH',
        'netherlands': 'NL', 'dutch': 'NL',
        'sweden': 'SE', 'swedish': 'SE',
        'norway': 'NO', 'norwegian': 'NO',
        'denmark': 'DK', 'danish': 'DK',
        'spain': 'ES', 'spanish': 'ES',
        'italy': 'IT', 'italian': 'IT',
    }
    
    # Infer country from text if not provided
    if not country_hint:
        text_lower = text.lower()
        inferred_countries = []
        for country_name, code in COUNTRY_NAMES.items():
            if country_name in text_lower:
                inferred_countries.append(code)
        if inferred_countries:
            country_hint = max(set(inferred_countries), key=inferred_countries.count)
    
    # Extract candidate company names
    candidates = _extract_candidates(text)
    
    # Try to match each candidate
    results = []
    seen = set()  # Avoid duplicates
    
    for candidate in candidates:
        mention = candidate['mention']
        
        # Try to match with country hint
        result = resolve_company(mention, country=country_hint)
        
        if result['final'] and result['final']['score'] >= min_confidence:
            company = result['final']
            
            # Deduplicate by company name
            if company['name'] in seen:
                continue
            seen.add(company['name'])
            
            results.append({
                'mention': mention,
                'name': company['name'],
                'country': company.get('country'),
                'lei': company.get('lei'),
                'wikidata_qid': company.get('wikidata_qid'),
                'score': company['score'],
                'context': candidate['context'],
                'decision': result['decision'],
            })
    
    # Sort by position in text
    results.sort(key=lambda x: text.index(x['mention']))
    
    return results


def _extract_candidates(text: str) -> List[Dict[str, Any]]:
    """Extract potential company name candidates from text."""
    candidates = []
    
    # Pattern 1: Phrases with legal suffixes
    legal_pattern = re.compile(
        r'\b([A-Z][A-Za-z0-9&\-]+(?:\s+[A-Z][A-Za-z0-9&\-]+)*)\s+(Inc\.?|Ltd\.?|Corp\.?|Corporation|Limited|Company|plc|LLC|L\.L\.C\.)\b',
        re.IGNORECASE
    )
    for match in legal_pattern.finditer(text):
        full_match = match.group(0)
        start = match.start()
        end = match.end()
        context = text[max(0, start-30):min(len(text), end+30)]
        candidates.append({
            'mention': full_match.strip(),
            'start': start,
            'end': end,
            'context': context.strip()
        })
    
    # Pattern 2: Capitalized phrases (2-4 consecutive capitalized words)
    cap_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b')
    for match in cap_pattern.finditer(text):
        mention = match.group(0)
        start = match.start()
        end = match.end()
        
        # Skip if already captured by legal suffix pattern
        if any(c['start'] <= start < c['end'] or c['start'] < end <= c['end'] for c in candidates):
            continue
        
        # Skip common words that aren't companies
        skip_words = {'The', 'This', 'That', 'These', 'Those', 'There', 'When', 'Where', 'What', 'Which'}
        if mention.split()[0] in skip_words:
            continue
        
        context = text[max(0, start-30):min(len(text), end+30)]
        candidates.append({
            'mention': mention,
            'start': start,
            'end': end,
            'context': context.strip()
        })
    
    # Deduplicate overlapping candidates (keep longer ones)
    filtered_candidates = []
    for candidate in sorted(candidates, key=lambda x: (x['start'], -(x['end'] - x['start']))):
        if not any(
            c['start'] <= candidate['start'] < c['end'] or 
            c['start'] < candidate['end'] <= c['end']
            for c in filtered_candidates
        ):
            filtered_candidates.append(candidate)
    
    return filtered_candidates

