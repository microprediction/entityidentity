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
from io import StringIO, BytesIO
import time


def load_asx(cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Load ASX (Australian Securities Exchange) listed companies.
    
    Data source: https://www.asx.com.au/asx/research/ASXListedCompanies.csv
    Format: CSV, updated regularly
    
    Returns:
        DataFrame with columns:
        - ticker: ASX ticker code
        - name: Company name
        - country: Always 'AU'
        - exchange: Always 'ASX'
        - industry: GICS industry classification (if available)
        
    Note:
        The ASX provides a downloadable CSV of all listed entities.
        Many mining companies are listed here (~2,300 companies).
    """
    # Official ASX listed companies CSV
    url = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
    
    try:
        response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Parse CSV - skip first few metadata rows
        lines = response.text.split('\n')
        # Find the header line (starts with "ASX code" or "Company name")
        header_idx = 0
        for i, line in enumerate(lines):
            if 'ASX code' in line or 'Company name' in line:
                header_idx = i
                break
        
        # Read CSV starting from header
        df = pd.read_csv(StringIO('\n'.join(lines[header_idx:])))
        
        # Normalize column names (ASX format varies)
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'asx code' in col_lower or col_lower == 'code':
                column_mapping[col] = 'ticker'
            elif 'company name' in col_lower or col_lower == 'name':
                column_mapping[col] = 'name'
            elif 'industry' in col_lower or 'gics' in col_lower:
                column_mapping[col] = 'industry'
        
        df = df.rename(columns=column_mapping)
        
        # Ensure required columns exist
        if 'ticker' not in df.columns or 'name' not in df.columns:
            raise ValueError(f"Could not find required columns in ASX data. Found: {df.columns.tolist()}")
        
        df['country'] = 'AU'
        df['exchange'] = 'ASX'
        
        # Select columns (industry might not exist)
        cols = ['ticker', 'name', 'country', 'exchange']
        if 'industry' in df.columns:
            cols.append('industry')
        
        result = df[cols].copy()
        
        # Clean up ticker and name
        result['ticker'] = result['ticker'].astype(str).str.strip()
        result['name'] = result['name'].astype(str).str.strip()
        
        # Remove empty rows
        result = result[result['ticker'].notna() & (result['ticker'] != '') & (result['ticker'] != 'nan')]
        
        print(f"Loaded {len(result)} companies from ASX")
        return result
        
    except Exception as e:
        print(f"Failed to fetch ASX data: {e}")
        print("Using sample data...")
        return sample_asx_data()


def load_lse(cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Load LSE (London Stock Exchange) listed companies.
    
    Data source: Wikipedia FTSE 350 constituents list (reliable structured data)
    Format: HTML table
    
    Returns:
        DataFrame with columns:
        - ticker: LSE ticker code
        - name: Company name
        - country: Primarily 'GB'
        - exchange: Always 'LSE'
        
    Note:
        We fetch FTSE 350 constituents from Wikipedia as a reliable proxy
        for major LSE companies (~350 companies including all major miners).
        Many UK mining companies (Anglo American, Glencore, Antofagasta, etc.) are in FTSE 100.
    """
    # Wikipedia has well-structured, maintained lists of FTSE constituents
    urls = [
        "https://en.wikipedia.org/wiki/FTSE_100_Index",  # Top 100
        "https://en.wikipedia.org/wiki/FTSE_250_Index",  # Next 250
    ]
    
    all_companies = []
    
    for url in urls:
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Wikipedia tables are well-structured
            tables = pd.read_html(StringIO(response.text))
            
            # Find the constituents table (usually labeled "Constituents" or "Components")
            for table in tables:
                if 'Company' in table.columns or 'EPIC' in table.columns or 'Ticker' in table.columns:
                    df = table.copy()
                    
                    # Normalize columns
                    column_mapping = {}
                    for col in df.columns:
                        col_lower = str(col).lower().strip()
                        if 'epic' in col_lower or 'ticker' in col_lower:
                            column_mapping[col] = 'ticker'
                        elif 'company' in col_lower or 'name' in col_lower:
                            column_mapping[col] = 'name'
                        elif 'sector' in col_lower or 'industry' in col_lower:
                            column_mapping[col] = 'industry'
                    
                    df = df.rename(columns=column_mapping)
                    
                    if 'ticker' in df.columns and 'name' in df.columns:
                        df['country'] = 'GB'
                        df['exchange'] = 'LSE'
                        
                        cols = ['ticker', 'name', 'country', 'exchange']
                        if 'industry' in df.columns:
                            cols.append('industry')
                        
                        result = df[cols].copy()
                        result['ticker'] = result['ticker'].astype(str).str.strip()
                        result['name'] = result['name'].astype(str).str.strip()
                        result = result[result['ticker'].notna() & (result['ticker'] != '') & (result['ticker'] != 'nan')]
                        
                        all_companies.append(result)
                        print(f"   Loaded {len(result)} companies from {url.split('/')[-1]}")
                        break
                    
        except Exception as e:
            print(f"   Warning: Could not fetch from {url}: {e}")
            continue
    
    if all_companies:
        combined = pd.concat(all_companies, ignore_index=True)
        # Deduplicate by ticker
        combined = combined.drop_duplicates(subset=['ticker'], keep='first')
        print(f"Loaded {len(combined)} companies from LSE (FTSE 100 + 250)")
        return combined
    else:
        print("Failed to fetch LSE data from any source.")
        print("Using sample data...")
        return sample_lse_data()


def load_tsx(cache_dir: Optional[str] = None) -> pd.DataFrame:
    """Load TSX/TSXV (Toronto Stock Exchange) listed companies.
    
    Data source: Wikipedia S&P/TSX Composite Index constituents (reliable structured data)
    Format: HTML table
    
    Returns:
        DataFrame with columns:
        - ticker: TSX ticker symbol
        - name: Company name
        - country: Primarily 'CA'
        - exchange: 'TSX'
        
    Note:
        We fetch S&P/TSX Composite constituents from Wikipedia as a reliable proxy
        for major TSX companies (~250 companies including all major Canadian miners).
        Many Canadian mining companies (Barrick Gold, Franco-Nevada, etc.) are listed here.
    """
    # Wikipedia has well-structured TSX index data
    urls = [
        "https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index",  # TSX Composite (~250 companies)
        "https://en.wikipedia.org/wiki/S%26P/TSX_60",  # TSX 60 (largest companies)
    ]
    
    all_companies = []
    
    for url in urls:
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Wikipedia tables are well-structured
            tables = pd.read_html(StringIO(response.text))
            
            # Find the constituents table
            for table in tables:
                if 'Company' in table.columns or 'Symbol' in table.columns or 'Ticker' in table.columns:
                    df = table.copy()
                    
                    # Normalize columns
                    column_mapping = {}
                    for col in df.columns:
                        col_lower = str(col).lower().strip()
                        if 'symbol' in col_lower or 'ticker' in col_lower:
                            column_mapping[col] = 'ticker'
                        elif 'company' in col_lower or 'name' in col_lower:
                            column_mapping[col] = 'name'
                        elif 'sector' in col_lower or 'industry' in col_lower:
                            column_mapping[col] = 'industry'
                    
                    df = df.rename(columns=column_mapping)
                    
                    if 'ticker' in df.columns and 'name' in df.columns:
                        # Reset index to avoid issues
                        df = df.reset_index(drop=True)
                        df['country'] = 'CA'
                        df['exchange'] = 'TSX'
                        
                        cols = ['ticker', 'name', 'country', 'exchange']
                        if 'industry' in df.columns:
                            cols.append('industry')
                        
                        result = df[cols].copy()
                        result = result.reset_index(drop=True)  # Ensure clean index
                        result['ticker'] = result['ticker'].astype(str).str.strip()
                        result['name'] = result['name'].astype(str).str.strip()
                        result = result[result['ticker'].notna() & (result['ticker'] != '') & (result['ticker'] != 'nan')]
                        result = result.reset_index(drop=True)  # Reset again after filtering
                        
                        all_companies.append(result)
                        print(f"   Loaded {len(result)} companies from {url.split('/')[-1]}")
                        break
                    
        except Exception as e:
            print(f"   Warning: Could not fetch from {url}: {e}")
            continue
    
    if all_companies:
        # Ensure all dataframes have the same columns before concatenating
        cleaned_dfs = []
        for i, df in enumerate(all_companies):
            # Ensure columns are unique by checking for duplicates
            if len(df.columns) != len(set(df.columns)):
                # Remove duplicate columns
                df = df.loc[:, ~df.columns.duplicated()]
            
            # Select only the columns we need
            base_cols = ['ticker', 'name', 'country', 'exchange']
            if 'industry' in df.columns:
                cols_to_keep = base_cols + ['industry']
            else:
                cols_to_keep = base_cols
            
            # Create clean dataframe with only needed columns
            clean_df = df[cols_to_keep].copy()
            clean_df = clean_df.reset_index(drop=True)
            cleaned_dfs.append(clean_df)
        
        combined = pd.concat(cleaned_dfs, ignore_index=True)
        # Deduplicate by ticker
        combined = combined.drop_duplicates(subset=['ticker'], keep='first')
        print(f"Loaded {len(combined)} companies from TSX")
        return combined
    else:
        print("Failed to fetch TSX data from any source.")
        print("Using sample data...")
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

