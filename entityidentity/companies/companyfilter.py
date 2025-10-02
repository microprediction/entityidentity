"""Company sector classification and filtering.

This module provides multiple strategies for filtering mining/energy companies:

1. **LLM Classification (Accurate but Expensive)**
   - Uses OpenAI/Anthropic models for intelligent classification
   - Understands industry context, supply/demand chains, diversified companies
   - ~3 companies/second, API costs apply
   - Best for: Production databases, research, high-accuracy needs

2. **Keyword Filtering (Fast but Simple)**
   - Rule-based matching on names, keywords, industry codes
   - ~10,000 companies/second, no API costs
   - Best for: Quick filtering, CI/CD, large datasets with tight budgets

3. **Hybrid Mode (Balanced)**
   - Keywords filter first (~90% reduction), then LLM refines
   - Combines speed and accuracy
   - Best for: Most use cases

Usage:
    # LLM-only (most accurate)
    filter_companies_llm(df, strategy='llm')

    # Keyword-only (fastest)
    filter_companies_llm(df, strategy='keyword')

    # Hybrid (recommended)
    filter_companies_llm(df, strategy='hybrid')
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from tqdm import tqdm
import yaml

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def load_config(config_path: Optional[Path] = None) -> Dict:
    """Load classifier configuration from YAML file."""
    if config_path is None:
        # Default config location
        config_path = Path(__file__).parent / 'company_classifier_config.yaml'
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def classify_company_openai(
    company_info: Dict,
    model: str = "gpt-4o-mini",
    client = None,
    config: Dict = None
) -> Tuple[bool, str, str, float, str, List[str]]:
    """Classify a company using OpenAI.
    
    Args:
        company_info: Dict with name, country, aliases, etc.
        model: OpenAI model to use
        client: OpenAI client instance
        config: Configuration dict with prompts
        
    Returns:
        (is_relevant, category, reasoning, confidence, metal_intensity, key_activities)
    """
    # Build sector definitions
    mining_def = "\n".join([f"  - {item}" for item in config['categories']['supply']['sectors']['mining']['includes']])
    recycling_def = "\n".join([f"  - {item}" for item in config['categories']['supply']['sectors']['recycling']['includes']])
    automotive_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['automotive']['includes']])
    manufacturing_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['manufacturing']['includes']])
    construction_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['construction']['includes']])
    electronics_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['electronics']['includes']])
    appliances_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['appliances']['includes']])
    
    # Format aliases
    aliases_str = ', '.join(company_info.get('aliases', [])[:3]) or 'None'
    
    # Build optional fields
    optional_fields = []
    if company_info.get('lei'):
        optional_fields.append(f"- LEI: {company_info['lei']}")
    if company_info.get('industry'):
        optional_fields.append(f"- Industry: {company_info['industry']}")
    optional_fields_str = '\n    '.join(optional_fields) if optional_fields else ''
    
    # Format prompts from config
    user_prompt = config['prompts']['user_template'].format(
        name=company_info['name'],
        country=company_info.get('country', 'Unknown'),
        aliases=aliases_str,
        optional_fields=optional_fields_str,
        mining_definition=mining_def,
        recycling_definition=recycling_def,
        automotive_definition=automotive_def,
        manufacturing_definition=manufacturing_def,
        construction_definition=construction_def,
        electronics_definition=electronics_def,
        appliances_definition=appliances_def
    )
    
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": config['prompts']['system']},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=config['models']['openai'].get('max_tokens', 400),
        )
        elapsed = time.time() - start_time
    except Exception as e:
        elapsed = time.time() - start_time
        # Re-raise with timing info
        raise type(e)(f"{str(e)} (after {elapsed:.1f}s)") from e
    
    result = json.loads(response.choices[0].message.content)
    result['_api_time'] = elapsed
    return (
        result['is_relevant'],
        result.get('category', 'neither'),
        result['reasoning'],
        result['confidence'],
        result.get('metal_intensity', 'unknown'),
        result.get('key_activities', [])
    )


def classify_company_anthropic(
    company_info: Dict,
    model: str = "claude-3-haiku-20240307",
    client = None,
    config: Dict = None
) -> Tuple[bool, str, str, float, str, List[str]]:
    """Classify a company using Anthropic Claude.
    
    Args:
        company_info: Dict with name, country, aliases, etc.
        model: Claude model to use
        client: Anthropic client instance
        config: Configuration dict with prompts
        
    Returns:
        (is_relevant, category, reasoning, confidence, metal_intensity, key_activities)
    """
    # Build sector definitions
    mining_def = "\n".join([f"  - {item}" for item in config['categories']['supply']['sectors']['mining']['includes']])
    recycling_def = "\n".join([f"  - {item}" for item in config['categories']['supply']['sectors']['recycling']['includes']])
    automotive_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['automotive']['includes']])
    manufacturing_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['manufacturing']['includes']])
    construction_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['construction']['includes']])
    electronics_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['electronics']['includes']])
    appliances_def = "\n".join([f"  - {item}" for item in config['categories']['demand']['sectors']['appliances']['includes']])
    
    # Format aliases
    aliases_str = ', '.join(company_info.get('aliases', [])[:3]) or 'None'
    
    # Build optional fields
    optional_fields = []
    if company_info.get('lei'):
        optional_fields.append(f"- LEI: {company_info['lei']}")
    if company_info.get('industry'):
        optional_fields.append(f"- Industry: {company_info['industry']}")
    optional_fields_str = '\n    '.join(optional_fields) if optional_fields else ''
    
    # Format prompts from config
    user_prompt = config['prompts']['user_template'].format(
        name=company_info['name'],
        country=company_info.get('country', 'Unknown'),
        aliases=aliases_str,
        optional_fields=optional_fields_str,
        mining_definition=mining_def,
        recycling_definition=recycling_def,
        automotive_definition=automotive_def,
        manufacturing_definition=manufacturing_def,
        construction_definition=construction_def,
        electronics_definition=electronics_def,
        appliances_definition=appliances_def
    )
    
    start_time = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=config['models']['anthropic'].get('max_tokens', 400),
            system=config['prompts']['system'],
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        elapsed = time.time() - start_time
    except Exception as e:
        elapsed = time.time() - start_time
        # Re-raise with timing info
        raise type(e)(f"{str(e)} (after {elapsed:.1f}s)") from e
    
    content = response.content[0].text
    # Extract JSON from response
    start = content.find('{')
    end = content.rfind('}') + 1
    result = json.loads(content[start:end])
    result['_api_time'] = elapsed
    
    return (
        result['is_relevant'],
        result.get('category', 'neither'),
        result['reasoning'],
        result['confidence'],
        result.get('metal_intensity', 'unknown'),
        result.get('key_activities', [])
    )


# ============================================================================
# Keyword-based filtering (fast, simple)
# ============================================================================

# Known major mining/energy companies (whitelist for edge cases)
KNOWN_MINING_ENERGY_COMPANIES = [
    'anglo american', 'bhp', 'rio tinto', 'vale', 'glencore',
    'freeport', 'newmont', 'barrick', 'southern copper',
    'exxon', 'chevron', 'shell', 'bp', 'totalenergies',
    'conocophillips', 'equinor', 'eni', 'petrobras',
]

# Mining and Energy sector keywords and codes
MINING_KEYWORDS = [
    'mining', 'mine', 'mineral', 'metals', 'gold', 'silver', 'copper',
    'iron', 'steel', 'aluminum', 'zinc', 'lead', 'nickel', 'lithium',
    'rare earth', 'coal', 'diamond', 'platinum', 'palladium', 'uranium',
    'exploration', 'ore', 'quarry', 'extraction', 'smelter', 'refinery',
    'resources', 'commodities', 'cobre', 'minera', 'miner'
]

ENERGY_KEYWORDS = [
    'energy', 'oil', 'gas', 'petroleum', 'lng', 'lpg', 'pipeline',
    'drilling', 'offshore', 'onshore', 'refining', 'exploration',
    'power', 'electric', 'electricity', 'utility', 'utilities',
    'solar', 'wind', 'renewable', 'hydro', 'nuclear', 'geothermal',
    'coal', 'battery', 'storage', 'grid', 'transmission'
]

# GICS Industry Codes (Level 2 - Industry Group)
GICS_CODES = ['10', '15', '1010', '1510']

# NAICS Codes
NAICS_CODES = ['21', '211', '212', '213', '221', '2211', '2212']

# NACE Codes (EU)
NACE_CODES = ['B', 'D', '05', '06', '07', '08', '09', '35']


def matches_mining_energy_keyword(row: pd.Series) -> bool:
    """Check if a company matches mining or energy criteria using keywords.

    Fast rule-based filtering without API calls.

    Args:
        row: DataFrame row with company data

    Returns:
        True if company is in mining/energy sector
    """
    # Check name against known companies whitelist first
    name = str(row.get('name', '')).lower()
    name_normalized = str(row.get('name_norm', '')).lower()

    for known_company in KNOWN_MINING_ENERGY_COMPANIES:
        if known_company in name or known_company in name_normalized:
            return True

    # Check name for keywords
    if any(keyword in name for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
        return True

    # Check industry field if available
    if 'industry' in row.index and pd.notna(row['industry']):
        industry = str(row['industry']).lower()
        if any(keyword in industry for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
            return True

    # Check sector field if available
    if 'sector' in row.index and pd.notna(row['sector']):
        sector = str(row['sector']).lower()
        if any(keyword in sector for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
            return True

    # Check GICS code if available
    if 'gics' in row.index and pd.notna(row['gics']):
        gics = str(row['gics'])
        if any(gics.startswith(code) for code in GICS_CODES):
            return True

    # Check NAICS code if available
    if 'naics' in row.index and pd.notna(row['naics']):
        naics = str(row['naics'])
        if any(naics.startswith(code) for code in NAICS_CODES):
            return True

    # Check NACE code if available
    if 'nace' in row.index and pd.notna(row['nace']):
        nace = str(row['nace']).upper()
        if any(nace.startswith(code) for code in NACE_CODES):
            return True

    # Check aliases for keywords
    if 'aliases' in row.index and isinstance(row['aliases'], list):
        for alias in row['aliases']:
            alias_lower = str(alias).lower()
            if any(keyword in alias_lower for keyword in MINING_KEYWORDS + ENERGY_KEYWORDS):
                return True

    return False


def filter_companies_keyword(df: pd.DataFrame) -> pd.DataFrame:
    """Filter companies using keyword-based rules (fast, no API costs).

    Args:
        df: Input DataFrame with company data

    Returns:
        Filtered DataFrame containing likely mining/energy companies
    """
    print(f"Filtering using keyword-based rules...")
    print(f"Total companies: {len(df):,}")

    # Apply filter
    mask = df.apply(matches_mining_energy_keyword, axis=1)
    filtered = df[mask].copy()

    print(f"✅ Matched companies: {len(filtered):,} ({len(filtered)/len(df)*100:.1f}%)")

    return filtered


# ============================================================================
# Cache management
# ============================================================================

def load_cache(cache_file: Optional[Path]) -> Dict:
    """Load classification cache."""
    if cache_file:
        cache_path = Path(cache_file) if isinstance(cache_file, str) else cache_file
        if cache_path.exists():
            with open(cache_path) as f:
                return json.load(f)
    return {}


def save_cache(cache: Dict, cache_file: Optional[Path]):
    """Save classification cache."""
    if cache_file:
        cache_path = Path(cache_file) if isinstance(cache_file, str) else cache_file
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)


def filter_companies_llm(
    df: pd.DataFrame,
    provider: str = "openai",
    model: Optional[str] = None,
    cache_file: Optional[Path] = None,
    confidence_threshold: float = 0.7,
    batch_size: int = 100,
    config_path: Optional[Path] = None,
    _internal_call: bool = False,
) -> pd.DataFrame:
    """Filter companies using LLM classification only.

    Args:
        df: Input DataFrame with company data
        provider: LLM provider (openai or anthropic)
        model: Model name (defaults based on provider)
        cache_file: Path to cache file for classifications
        confidence_threshold: Minimum confidence to include company
        batch_size: Number of companies to process before saving cache
        config_path: Path to config file (defaults to package config)
        _internal_call: Internal flag to suppress header (used by hybrid mode)

    Returns:
        Filtered DataFrame containing only mining/energy companies
    """
    # Load configuration
    config = load_config(config_path)
    if not _internal_call:
        print(f"Loaded configuration")
    
    # Filter out companies with empty names
    original_count = len(df)
    df = df[df['name'].notna() & (df['name'] != '')].copy()
    if len(df) < original_count:
        print(f"⚠️  Removed {original_count - len(df)} companies with empty names")
    
    # Initialize LLM client
    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI()
            model = model or config['models']['openai']['default']
            classify_fn = classify_company_openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    elif provider == "anthropic":
        try:
            from anthropic import Anthropic
            client = Anthropic()
            model = model or config['models']['anthropic']['default']
            classify_fn = classify_company_anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    print(f"Using {provider} with model {model}")
    print(f"Total companies: {len(df):,}")
    
    # Load cache
    cache = load_cache(cache_file)
    print(f"Cached classifications: {len(cache):,}")
    
    # Classify companies
    print(f"Classifying companies (confidence threshold: {confidence_threshold})...")
    
    results = []
    processed = 0
    api_times = []  # Track API response times
    slow_requests = 0  # Count of slow requests (potential rate limiting)
    
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        # Create cache key
        cache_key = f"{row['name']}|{row.get('country', '')}"
        
        # Check cache
        if cache_key in cache:
            is_relevant = cache[cache_key]['is_relevant']
            confidence = cache[cache_key]['confidence']
            category = cache[cache_key].get('category', 'neither')
        else:
            # Classify using LLM
            company_info = {
                'name': row['name'],
                'country': row.get('country', ''),
                'aliases': row.get('aliases', []) if isinstance(row.get('aliases'), list) else [],
                'lei': row.get('lei', ''),
                'industry': row.get('industry', '')
            }
            
            try:
                # Measure API call time
                request_start = time.time()
                is_relevant, category, reasoning, confidence, metal_intensity, key_activities = classify_fn(
                    company_info, model, client, config
                )
                api_time = time.time() - request_start
                
                # Cache result
                cache[cache_key] = {
                    'is_relevant': is_relevant,
                    'category': category,
                    'reasoning': reasoning,
                    'confidence': confidence,
                    'metal_intensity': metal_intensity,
                    'key_activities': key_activities,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Track API response time
                api_times.append(api_time)
                
                # Detect slow requests (potential rate limiting/backoff)
                if api_time > 5.0:
                    slow_requests += 1
                    tqdm.write(f"⚠️  Slow request detected: {api_time:.1f}s for {row['name'][:30]} (rate limit?)")
                
                # Save cache periodically with diagnostics
                processed += 1
                if processed % batch_size == 0:
                    save_cache(cache, cache_file)
                    avg_time = sum(api_times[-batch_size:]) / min(batch_size, len(api_times))
                    recent_slow = sum(1 for t in api_times[-batch_size:] if t > 5.0)
                    tqdm.write(f"\n📊 Batch stats (last {batch_size}):")
                    tqdm.write(f"   Avg API time: {avg_time:.2f}s")
                    tqdm.write(f"   Slow requests: {recent_slow} (>{5}s, possible rate limiting)")
                    tqdm.write(f"   Cached: {len(cache):,} classifications")
                
            except Exception as e:
                error_msg = str(e)
                tqdm.write(f"\n❌ Error classifying {row['name']}: {error_msg}")
                
                # Check for rate limit errors
                if 'rate_limit' in error_msg.lower() or '429' in error_msg:
                    tqdm.write(f"🔴 RATE LIMIT detected - API is throttling requests!")
                elif 'timeout' in error_msg.lower():
                    tqdm.write(f"🔴 TIMEOUT detected - API response taking too long!")
                
                is_relevant = False
                confidence = 0.0
                category = 'neither'
        
        # Include if above confidence threshold and relevant
        if is_relevant and confidence >= confidence_threshold:
            # Add category column to track supply vs demand
            df.at[idx, 'value_chain_category'] = category
            results.append(idx)
    
    # Save final cache
    save_cache(cache, cache_file)
    
    # Print API timing statistics
    if api_times:
        print(f"\n📊 API Performance Statistics:")
        print(f"   Total API calls: {len(api_times):,}")
        print(f"   Avg response time: {sum(api_times)/len(api_times):.2f}s")
        print(f"   Min/Max: {min(api_times):.2f}s / {max(api_times):.2f}s")
        print(f"   Slow requests (>5s): {slow_requests} ({slow_requests/len(api_times)*100:.1f}%)")
        if slow_requests > len(api_times) * 0.1:
            print(f"   ⚠️  High rate of slow requests - likely experiencing rate limiting!")
    
    # Filter dataframe
    filtered = df.loc[results].copy()
    
    print(f"\n✅ Matched companies: {len(filtered):,} ({len(filtered)/len(df)*100:.1f}%)")
    
    # Deduplicate by (name, country) - keep first occurrence
    original_filtered_count = len(filtered)
    filtered = filtered.drop_duplicates(subset=['name', 'country'], keep='first')
    if len(filtered) < original_filtered_count:
        print(f"⚠️  Removed {original_filtered_count - len(filtered)} duplicate companies")
    
    # Show breakdown by category
    if 'value_chain_category' in filtered.columns:
        print("\nBreakdown by value chain position:")
        for cat, count in filtered['value_chain_category'].value_counts().items():
            print(f"  - {cat:10s}: {count:6,} companies")
    
    return filtered


# ============================================================================
# Unified API with strategy selection
# ============================================================================

def filter_companies(
    df: pd.DataFrame,
    strategy: str = "hybrid",
    provider: str = "openai",
    model: Optional[str] = None,
    cache_file: Optional[Path] = None,
    confidence_threshold: float = 0.7,
    batch_size: int = 100,
    config_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Filter companies using selected strategy.

    Args:
        df: Input DataFrame with company data
        strategy: Filtering strategy ('llm', 'keyword', or 'hybrid')
        provider: LLM provider for LLM/hybrid modes (openai or anthropic)
        model: Model name (defaults based on provider)
        cache_file: Path to cache file for LLM classifications
        confidence_threshold: Minimum confidence to include company (LLM only)
        batch_size: Number of companies to process before saving cache (LLM only)
        config_path: Path to config file (defaults to package config)

    Returns:
        Filtered DataFrame containing only mining/energy companies

    Examples:
        >>> # Fast keyword-only filtering
        >>> filtered = filter_companies(df, strategy='keyword')

        >>> # Most accurate LLM-only filtering
        >>> filtered = filter_companies(df, strategy='llm', provider='openai')

        >>> # Balanced hybrid approach (recommended)
        >>> filtered = filter_companies(df, strategy='hybrid', provider='openai')
    """
    if strategy == "keyword":
        return filter_companies_keyword(df)
    elif strategy == "llm":
        return filter_companies_llm(
            df=df,
            provider=provider,
            model=model,
            cache_file=cache_file,
            confidence_threshold=confidence_threshold,
            batch_size=batch_size,
            config_path=config_path
        )
    elif strategy == "hybrid":
        return filter_companies_hybrid(
            df=df,
            provider=provider,
            model=model,
            cache_file=cache_file,
            confidence_threshold=confidence_threshold,
            batch_size=batch_size,
            config_path=config_path
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}. Use 'llm', 'keyword', or 'hybrid'")


def filter_companies_hybrid(
    df: pd.DataFrame,
    provider: str = "openai",
    model: Optional[str] = None,
    cache_file: Optional[Path] = None,
    confidence_threshold: float = 0.7,
    batch_size: int = 100,
    config_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Filter companies using hybrid strategy (keyword pre-filter + LLM refinement).

    This is the recommended approach for most use cases:
    1. Apply fast keyword filtering to reduce dataset by ~90%
    2. Use LLM to refine results and eliminate false positives

    Args:
        df: Input DataFrame with company data
        provider: LLM provider (openai or anthropic)
        model: Model name (defaults based on provider)
        cache_file: Path to cache file for classifications
        confidence_threshold: Minimum confidence to include company
        batch_size: Number of companies to process before saving cache
        config_path: Path to config file (defaults to package config)

    Returns:
        Filtered DataFrame containing only mining/energy companies
    """
    print("=" * 70)
    print("  HYBRID FILTERING STRATEGY")
    print("=" * 70)
    print()

    # Stage 1: Keyword pre-filtering
    print("📍 Stage 1: Keyword Pre-filtering")
    print("-" * 70)
    keyword_filtered = filter_companies_keyword(df)
    reduction_pct = (1 - len(keyword_filtered) / len(df)) * 100
    print(f"   Reduced dataset by {reduction_pct:.1f}% ({len(df):,} → {len(keyword_filtered):,} companies)")
    print()

    # Stage 2: LLM refinement
    print("📍 Stage 2: LLM Refinement")
    print("-" * 70)
    final_filtered = filter_companies_llm(
        df=keyword_filtered,
        provider=provider,
        model=model,
        cache_file=cache_file,
        confidence_threshold=confidence_threshold,
        batch_size=batch_size,
        config_path=config_path,
        _internal_call=True
    )

    print()
    print("=" * 70)
    print("  HYBRID FILTERING RESULTS")
    print("=" * 70)
    print(f"   Original dataset:     {len(df):6,} companies")
    print(f"   After keyword filter: {len(keyword_filtered):6,} companies ({len(keyword_filtered)/len(df)*100:5.1f}%)")
    print(f"   After LLM refinement: {len(final_filtered):6,} companies ({len(final_filtered)/len(df)*100:5.1f}%)")
    print(f"   False positive rate:  {(len(keyword_filtered) - len(final_filtered))/len(keyword_filtered)*100:5.1f}%")
    print("=" * 70)

    return final_filtered


def main():
    """CLI entry point for filtering companies."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Filter companies for mining/energy using LLM classification"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input parquet file with companies"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output parquet file for filtered companies"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider (default: openai)"
    )
    parser.add_argument(
        "--model",
        help="Model name (optional, uses provider default)"
    )
    parser.add_argument(
        "--cache-file",
        help="Path to cache file for classifications (enables caching)"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Minimum confidence to include company (default: 0.7)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of companies to process before saving cache (default: 100)"
    )
    parser.add_argument(
        "--config",
        help="Path to config YAML file (optional)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  LLM-based Company Filtering")
    print("=" * 70)
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Provider: {args.provider}")
    if args.cache_file:
        print(f"Cache: {args.cache_file} (enabled)")
    else:
        print("Cache: disabled (pass --cache-file to enable)")
    print("=" * 70)
    print()
    
    # Load input
    import pandas as pd
    from pathlib import Path
    
    df = pd.read_parquet(args.input)
    print(f"Loaded {len(df):,} companies from {args.input}")
    print()
    
    # Filter
    filtered = filter_companies_llm(
        df=df,
        provider=args.provider,
        model=args.model,
        cache_file=Path(args.cache_file) if args.cache_file else None,
        confidence_threshold=args.confidence_threshold,
        batch_size=args.batch_size,
        config_path=Path(args.config) if args.config else None,
    )
    
    # Save output
    filtered.to_parquet(args.output, index=False)
    print(f"\n💾 Saved {len(filtered):,} filtered companies to {args.output}")
    
    # Show stats
    size_mb = Path(args.output).stat().st_size / 1_000_000
    print(f"📊 File size: {size_mb:.2f} MB")
    print()
    print("=" * 70)
    print("✅ Filtering complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

