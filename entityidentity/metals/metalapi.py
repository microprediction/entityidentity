"""Metals entity resolution API.

Public API for metal identification and resolution.
This provides a clean, simple API for resolving metal names, symbols, and forms
to canonical metal entities with deterministic identifiers.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Union
import pandas as pd

# Import robust implementation from metalidentity
from entityidentity.metals.metalidentity import (
    resolve_metal as _resolve_metal,
    topk_matches as _topk_matches,
)
from entityidentity.utils.dataloader import (
    find_data_file,
    load_parquet_or_csv,
    format_not_found_error,
)


@lru_cache(maxsize=1)
def load_metals(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load compiled metals.parquet into memory.

    Uses LRU cache to load the metals DataFrame once and reuse it.
    This provides fast, memory-resident lookups for all metal resolution operations.

    Args:
        path: Optional path to metals.parquet file. If None, uses default location
              in entityidentity/metals/data/metals.parquet

    Returns:
        DataFrame with metal entities and all metadata columns:
          - metal_id: 16-hex deterministic hash
          - metal_key: Human-readable slug
          - symbol: IUPAC element symbol (if applicable)
          - name, name_norm: Display and normalized names
          - formula, code: Chemical formula and commercial codes
          - category_bucket: precious|base|battery|pgm|ree|ferroalloy|specialty|industrial
          - cluster_id: Supply-chain cluster assignment
          - default_unit, default_basis: Market quotation standards
          - alias1...alias10: Common aliases
          - and other metadata fields

    Examples:
        >>> df = load_metals()
        >>> df[['name', 'symbol', 'category_bucket']].head()
    """
    if path is None:
        # Use shared utility to find data file (metals data is in metals/data/)
        found_path = find_data_file(
            module_file=__file__,
            subdirectory="metals",
            filenames=["metals.parquet"],
            search_dev_tables=False,  # Metals data only in package, not tables/
            module_local_data=True,  # Check metals/data/ directory
        )

        if found_path is None:
            # Generate helpful error message
            metals_dir = Path(__file__).parent / "data"
            error_msg = format_not_found_error(
                subdirectory="metals",
                searched_locations=[
                    ("Module-local data", metals_dir),
                ],
                fix_instructions=[
                    "Run entityidentity/metals/data/build_metals.py to generate it.",
                ],
            )
            raise FileNotFoundError(error_msg)

        path = found_path

    # Load data using shared utility
    return load_parquet_or_csv(Path(path))


def metal_identifier(
    name: str,
    *,
    cluster: Optional[str] = None,
    category: Optional[str] = None,
    threshold: int = 90,
) -> Optional[dict]:
    """Return canonical metal row as dict or None.

    Resolves metal names, symbols, forms, and commercial specifications to
    canonical metal entities using a multi-stage blocking and fuzzy matching pipeline.

    Resolution strategy:
      1. Exact symbol match (e.g., "Pt" → Platinum)
      2. Category bucket filter (if specified)
      3. Name prefix blocking (first 3 chars normalized)
      4. Supply-chain cluster filter (if specified)
      5. Final scoring via RapidFuzz WRatio on names + aliases

    Supports "metal:form" hints (e.g., "lithium:carbonate" → lithium carbonate)

    Args:
        name: Metal name, symbol, form, or spec
              Examples: "Pt", "platinum", "APT", "lithium carbonate", "lithium:carbonate"
        cluster: Optional supply-chain cluster filter (e.g., "pgm_complex", "battery_chain")
        category: Optional category bucket filter (e.g., "pgm", "battery", "precious")
        threshold: Minimum fuzzy match score (0-100). Default 90.

    Returns:
        Dict with canonical metal fields, or None if no match above threshold.
        Dict contains: metal_id, metal_key, name, symbol, category_bucket, cluster_id,
                      default_unit, default_basis, and all other metadata fields.

    Examples:
        >>> metal_identifier("Pt")
        {'metal_id': '...', 'name': 'Platinum', 'symbol': 'Pt', ...}

        >>> metal_identifier("APT")
        {'metal_id': '...', 'name': 'Ammonium paratungstate', 'code': 'WO3', ...}

        >>> metal_identifier("lithium:carbonate")
        {'metal_id': '...', 'name': 'Lithium carbonate', 'formula': 'Li2CO3', ...}

        >>> metal_identifier("platinum", category="pgm")
        {'metal_id': '...', 'name': 'Platinum', 'category_bucket': 'pgm', ...}
    """
    df = load_metals()
    result = _resolve_metal(
        name=name,
        df=df,
        cluster=cluster,
        category=category,
        threshold=threshold,
    )

    if result is None:
        return None

    # Convert Series to dict
    return result.to_dict()


def match_metal(name: str, *, k: int = 5) -> list[dict]:
    """Top-K candidates + scores (for review UIs).

    Returns the top K metal candidates with their fuzzy match scores,
    useful for interactive review interfaces, disambiguation, and
    understanding resolution decisions.

    Args:
        name: Metal name, symbol, form, or spec to match
        k: Number of top candidates to return. Default 5.

    Returns:
        List of dicts, each containing:
          - All metal fields (metal_id, name, symbol, etc.)
          - score: Fuzzy match score (0-100)
        Ordered by descending score.

    Examples:
        >>> matches = match_metal("tungsten", k=3)
        >>> for m in matches:
        ...     print(f"{m['name']} ({m['symbol']}) - score: {m['score']}")
        Tungsten (W) - score: 100
        Ammonium paratungstate (None) - score: 85
        ...
    """
    df = load_metals()
    results = _topk_matches(name=name, df=df, k=k)

    # Convert list of (Series, score) tuples to list of dicts with scores
    return [
        {**row.to_dict(), "score": score}
        for row, score in results
    ]


def list_metals(
    cluster: Optional[str] = None,
    category: Optional[str] = None,
) -> pd.DataFrame:
    """List metals filtered by cluster and/or category.

    Returns the metals DataFrame filtered by supply-chain cluster
    and/or category bucket. Useful for exploring the ontology and
    understanding available metals in specific domains.

    Args:
        cluster: Optional supply-chain cluster filter
                 Examples: "pgm_complex", "porphyry_copper_chain", "battery_chain"
        category: Optional category bucket filter
                  Examples: "pgm", "precious", "base", "battery", "ree", "ferroalloy"

    Returns:
        Filtered DataFrame with metal entities

    Examples:
        >>> pgm_metals = list_metals(category="pgm")
        >>> pgm_metals[['name', 'symbol']].values
        array([['Platinum', 'Pt'], ['Palladium', 'Pd'], ...])

        >>> battery_chain = list_metals(cluster="lithium_chain")
        >>> battery_chain[['name', 'formula']].values
    """
    df = load_metals()

    # Apply filters
    if cluster is not None:
        df = df[df["cluster_id"] == cluster]

    if category is not None:
        df = df[df["category_bucket"] == category]

    return df


__all__ = [
    "load_metals",
    "metal_identifier",
    "match_metal",
    "list_metals",
]
