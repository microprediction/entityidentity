"""Stock exchange company list loaders.

Provides loaders for major stock exchanges that publish official company lists.
These are particularly useful for mining/resources companies.

Sources:
- ASX (Australian Securities Exchange)
- LSE (London Stock Exchange)
- TSX/TSXV (Toronto Stock Exchange)
- JSE (Johannesburg Stock Exchange)
- HKEX (Hong Kong Exchanges)
"""

from __future__ import annotations
import requests
from typing import Optional
import pandas as pd
from io import StringIO


def load_asx(cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Load ASX (Australian Securities Exchange) listed companies.
    
    Data source: https://www.asx.com.au/markets/trade-our-cash-market/directory/asx-listed-entities
    Format: CSV, updated daily
    
    Returns:
        DataFrame with columns:
        - ticker: ASX ticker code
        - name: Company name
        - country: Always 'AU'
        - exchange: Always 'ASX'
        - industry: GICS industry classification
        
    Note:
        The ASX provides a downloadable CSV of all listed entities.
        Many mining companies are listed here.
    """
    # Note: This URL may change. Check ASX website for current endpoint.
    # This is a placeholder - actual implementation needs the real CSV endpoint
    url = "https://asx.api.markitdigital.com/asx-research/1.0/companies/directory/file"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse CSV
        df = pd.read_csv(StringIO(response.text))
        
        # Normalize columns
        df = df.rename(columns={
            'ASX code': 'ticker',
            'Company name': 'name',
            'GICS industry group': 'industry',
        })
        
        df['country'] = 'AU'
        df['exchange'] = 'ASX'
        
        return df[['ticker', 'name', 'country', 'exchange', 'industry']]
        
    except requests.HTTPError:
        print("Failed to fetch ASX data. Using sample data...")
        return sample_asx_data()


def load_lse(cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Load LSE (London Stock Exchange) listed companies.
    
    Data source: https://www.londonstockexchange.com/indices/ftse-100/constituents/table
    Format: Varies (web scraping may be required)
    
    Returns:
        DataFrame with columns:
        - ticker: LSE ticker code
        - name: Company name
        - country: Primarily 'GB'
        - exchange: Always 'LSE'
        
    Note:
        LSE data access may require scraping or API key.
        Many UK mining companies are listed here.
    """
    # Placeholder implementation
    print("LSE data loader not fully implemented. Using sample data...")
    return sample_lse_data()


def load_tsx(cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Load TSX/TSXV (Toronto Stock Exchange) listed companies.
    
    Data source: https://www.tsx.com/listings/current-listings
    Format: Excel/CSV download available
    
    Returns:
        DataFrame with columns:
        - ticker: TSX ticker symbol
        - name: Company name
        - country: Primarily 'CA'
        - exchange: 'TSX' or 'TSXV'
        
    Note:
        Canada has many mining companies listed on TSX and TSX Venture.
    """
    # Placeholder implementation
    print("TSX data loader not fully implemented. Using sample data...")
    return sample_tsx_data()


def sample_asx_data() -> pd.DataFrame:
    """Sample ASX mining companies for testing."""
    data = [
        {'ticker': 'BHP', 'name': 'BHP Group Limited', 'country': 'AU', 'exchange': 'ASX', 'industry': 'Materials'},
        {'ticker': 'RIO', 'name': 'Rio Tinto Limited', 'country': 'AU', 'exchange': 'ASX', 'industry': 'Materials'},
        {'ticker': 'FMG', 'name': 'Fortescue Metals Group Ltd', 'country': 'AU', 'exchange': 'ASX', 'industry': 'Materials'},
        {'ticker': 'NCM', 'name': 'Newcrest Mining Limited', 'country': 'AU', 'exchange': 'ASX', 'industry': 'Materials'},
    ]
    return pd.DataFrame(data)


def sample_lse_data() -> pd.DataFrame:
    """Sample LSE mining companies for testing."""
    data = [
        {'ticker': 'AAL', 'name': 'Anglo American plc', 'country': 'GB', 'exchange': 'LSE'},
        {'ticker': 'GLEN', 'name': 'Glencore plc', 'country': 'GB', 'exchange': 'LSE'},
        {'ticker': 'ANTO', 'name': 'Antofagasta plc', 'country': 'GB', 'exchange': 'LSE'},
    ]
    return pd.DataFrame(data)


def sample_tsx_data() -> pd.DataFrame:
    """Sample TSX mining companies for testing."""
    data = [
        {'ticker': 'ABX', 'name': 'Barrick Gold Corporation', 'country': 'CA', 'exchange': 'TSX'},
        {'ticker': 'FNV', 'name': 'Franco-Nevada Corporation', 'country': 'CA', 'exchange': 'TSX'},
        {'ticker': 'WPM', 'name': 'Wheaton Precious Metals Corp.', 'country': 'CA', 'exchange': 'TSX'},
    ]
    return pd.DataFrame(data)

