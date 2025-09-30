"""LLM-based company sector classification and filtering.

This module provides intelligent company classification using LLMs to determine
if companies belong to mining or energy sectors.
"""

import json
import os
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
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": config['prompts']['system']},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=config['models']['openai'].get('max_tokens', 400),
    )
    
    result = json.loads(response.choices[0].message.content)
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
    
    response = client.messages.create(
        model=model,
        max_tokens=config['models']['anthropic'].get('max_tokens', 400),
        system=config['prompts']['system'],
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    
    content = response.content[0].text
    # Extract JSON from response
    start = content.find('{')
    end = content.rfind('}') + 1
    result = json.loads(content[start:end])
    
    return (
        result['is_relevant'],
        result.get('category', 'neither'),
        result['reasoning'],
        result['confidence'],
        result.get('metal_intensity', 'unknown'),
        result.get('key_activities', [])
    )


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
) -> pd.DataFrame:
    """Filter companies using LLM classification.
    
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
    # Load configuration
    config = load_config(config_path)
    print(f"Loaded configuration")
    
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
                is_relevant, category, reasoning, confidence, metal_intensity, key_activities = classify_fn(
                    company_info, model, client, config
                )
                
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
                
                # Save cache periodically
                processed += 1
                if processed % batch_size == 0:
                    save_cache(cache, cache_file)
                    print(f"\nSaved {len(cache)} classifications to cache")
                
            except Exception as e:
                print(f"\nError classifying {row['name']}: {e}")
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
    
    # Filter dataframe
    filtered = df.loc[results].copy()
    
    print(f"\n✅ Matched companies: {len(filtered):,} ({len(filtered)/len(df)*100:.1f}%)")
    
    # Show breakdown by category
    if 'value_chain_category' in filtered.columns:
        print("\nBreakdown by value chain position:")
        for cat, count in filtered['value_chain_category'].value_counts().items():
            print(f"  - {cat:10s}: {count:6,} companies")
    
    return filtered


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

