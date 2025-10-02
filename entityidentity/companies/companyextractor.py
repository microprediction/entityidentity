"""Text extraction utilities for finding company mentions."""

import re
from typing import List, Optional, Dict, Any

from entityidentity.companies.companyresolver import resolve_company, load_companies
from entityidentity.countries import country_identifier


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

    # Infer country from text if not provided
    if not country_hint:
        country_hint = _infer_country_from_text(text)
    
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


def _infer_country_from_text(text: str) -> Optional[str]:
    """Infer country context from text using existing country resolution.

    Extracts potential country mentions (capitalized words/phrases) and uses
    the robust country_identifier() to resolve them. No hardcoded list needed!

    Args:
        text: Text to analyze for country mentions

    Returns:
        ISO2 country code if found, None otherwise

    Examples:
        >>> _infer_country_from_text("Apple in the United States...")
        'US'
        >>> _infer_country_from_text("BHP operates in Australia")
        'AU'
    """
    # Extract capitalized word sequences (potential country names)
    # Match 1-3 word capitalized phrases
    potential_countries = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b', text)

    # Also check for common abbreviations and adjectives
    # Extract words that might be country-related
    words = re.findall(r'\b[A-Za-z]+\b', text.lower())

    # Try to identify countries using existing country_identifier
    # It handles all country names, abbreviations, colloquialisms, and fuzzy matching!
    inferred_countries = []

    # Check capitalized phrases (e.g., "United States", "South Africa")
    for phrase in potential_countries:
        code = country_identifier(phrase)
        if code:
            inferred_countries.append(code)

    # Check individual words (e.g., "USA", "American", "Dutch")
    for word in set(words):  # Use set to avoid duplicates
        if len(word) >= 2:  # Skip single letters
            code = country_identifier(word)
            if code:
                inferred_countries.append(code)

    if inferred_countries:
        # Return most common inferred country
        return max(set(inferred_countries), key=inferred_countries.count)

    return None


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

