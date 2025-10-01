"""Wikidata company data loader.

Wikidata provides rich company information with labels, aliases, historical names,
multilingual data, and links to external identifiers (LEI, stock tickers, etc.).

Data source: https://www.wikidata.org
Query endpoint: https://query.wikidata.org/sparql
Format: SPARQL queries returning JSON/CSV
"""

from __future__ import annotations
import requests
from typing import Optional, List, Dict, Any
import pandas as pd
from time import sleep


WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# User agent required by Wikidata
USER_AGENT = "EntityIdentity/0.0.1 (https://github.com/petercotton/entityidentity)"


def load_wikidata_companies(
    limit: Optional[int] = 10000,
    country_codes: Optional[List[str]] = None,
    include_dissolved: bool = False,
) -> pd.DataFrame:
    """Load company data from Wikidata.
    
    Queries for entities of type 'business' (Q4830453), 'company' (Q783794),
    'public company' (Q891723), etc.
    
    Args:
        limit: Maximum number of results (Wikidata may timeout on large queries)
        country_codes: Optional list of ISO country codes to filter by
        include_dissolved: Include companies that have been dissolved
        
    Returns:
        DataFrame with columns:
        - wikidata_qid: Wikidata Q-ID
        - name: Primary label (English preferred)
        - aliases: List of alternate names
        - country: ISO country code
        - lei: Legal Entity Identifier (if available)
        - stock_ticker: Stock exchange ticker (if available)
        - official_website: Official website URL
        - inception: Year founded
        
    Note:
        Wikidata rate limits apply. For large datasets, consider downloading
        the full Wikidata dump and processing locally.
    """
    
    # Build SPARQL query
    query = _build_company_query(limit, country_codes, include_dissolved)
    
    print(f"Querying Wikidata for up to {limit} companies...")
    
    try:
        results = _query_wikidata(query)
        df = _parse_wikidata_results(results)
        return df
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limited by Wikidata. Consider caching or using smaller queries.")
        raise


def _build_company_query(
    limit: int,
    country_codes: Optional[List[str]],
    include_dissolved: bool
) -> str:
    """Build SPARQL query for companies."""
    
    country_filter = ""
    if country_codes:
        countries_list = " ".join([f"wd:{code}" for code in country_codes])
        country_filter = f"VALUES ?country {{ {countries_list} }}"
    
    dissolved_filter = "FILTER NOT EXISTS { ?company wdt:P576 ?dissolved . }" if not include_dissolved else ""
    
    query = f"""
    SELECT DISTINCT ?company ?companyLabel ?lei ?country ?countryLabel 
           (GROUP_CONCAT(DISTINCT ?altLabel; separator="|") AS ?aliases)
           (SAMPLE(?website) AS ?official_website)
           (SAMPLE(?ticker) AS ?stock_ticker)
           (YEAR(SAMPLE(?founded)) AS ?inception)
    WHERE {{
      ?company wdt:P31/wdt:P279* wd:Q4830453 .  # Instance of business
      
      {country_filter}
      
      OPTIONAL {{ ?company wdt:P1278 ?lei . }}  # LEI
      OPTIONAL {{ ?company wdt:P17 ?country . }}  # Country
      OPTIONAL {{ ?company wdt:P856 ?website . }}  # Official website
      OPTIONAL {{ ?company wdt:P414 ?ticker . }}  # Stock ticker
      OPTIONAL {{ ?company wdt:P571 ?founded . }}  # Inception date
      OPTIONAL {{ ?company skos:altLabel ?altLabel . FILTER(LANG(?altLabel) = "en") }}
      
      {dissolved_filter}
      
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    GROUP BY ?company ?companyLabel ?lei ?country ?countryLabel
    LIMIT {limit}
    """
    
    return query


def _query_wikidata(query: str) -> Dict[str, Any]:
    """Execute SPARQL query against Wikidata."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    
    params = {
        "query": query,
        "format": "json",
    }
    
    response = requests.get(
        WIKIDATA_SPARQL_ENDPOINT,
        params=params,
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    
    return response.json()


def _parse_wikidata_results(results: Dict[str, Any]) -> pd.DataFrame:
    """Parse SPARQL JSON results into DataFrame."""
    bindings = results.get("results", {}).get("bindings", [])
    
    rows = []
    for item in bindings:
        row = {
            "wikidata_qid": _extract_qid(item.get("company", {}).get("value", "")),
            "name": item.get("companyLabel", {}).get("value", ""),
            "lei": item.get("lei", {}).get("value", ""),
            "country": _extract_country_code(item.get("country", {}).get("value", "")),
            "official_website": item.get("official_website", {}).get("value", ""),
            "stock_ticker": item.get("stock_ticker", {}).get("value", ""),
            "inception": item.get("inception", {}).get("value", ""),
            "aliases": item.get("aliases", {}).get("value", "").split("|") if item.get("aliases", {}).get("value") else [],
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


def _extract_qid(url: str) -> str:
    """Extract Q-ID from Wikidata entity URL."""
    if "/Q" in url:
        return "Q" + url.split("/Q")[1]
    return ""


def _extract_country_code(url: str) -> str:
    """Extract country code from Wikidata country entity.
    
    Note: This is simplified. Real implementation should map
    Wikidata country entities to ISO codes via a lookup.
    """
    # Simplified - in practice, query should return ISO code directly
    return ""


def sample_wikidata_data() -> pd.DataFrame:
    """Return a small sample of Wikidata-like company data for testing."""
    data = [
        {
            'wikidata_qid': 'Q312',
            'name': 'Apple Inc.',
            'lei': '529900HNOAA1KXQJUQ27',
            'country': 'US',
            'official_website': 'https://www.apple.com',
            'stock_ticker': 'AAPL',
            'inception': '1976',
            'alias1': 'Apple Computer',
            'alias2': 'Apple Computer, Inc.',
        },
        {
            'wikidata_qid': 'Q2283',
            'name': 'Microsoft Corporation',
            'lei': '549300FX7K9QRXDE7E94',
            'country': 'US',
            'official_website': 'https://www.microsoft.com',
            'stock_ticker': 'MSFT',
            'inception': '1975',
            'alias1': 'Microsoft Corp',
            'alias2': 'MSFT',
            'alias3': 'Microsoft',
        },
    ]
    return pd.DataFrame(data)

