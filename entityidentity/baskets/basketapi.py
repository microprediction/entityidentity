"""Baskets entity resolution API.

Public API for basket identification and resolution.
This provides a clean, simple API for resolving basket names
to canonical basket entities with deterministic identifiers.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Union
import pandas as pd

# Import robust implementation from basketidentity
from entityidentity.baskets.basketidentity import (
    resolve_basket as _resolve_basket,
    topk_matches as _topk_matches,
)
from entityidentity.utils.dataloader import (
    find_data_file,
    load_parquet_or_csv,
    format_not_found_error,
)


@lru_cache(maxsize=1)
def load_baskets(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load compiled baskets.parquet into memory.

    Uses LRU cache to load the baskets DataFrame once and reuse it.
    This provides fast, memory-resident lookups for all basket resolution operations.

    Args:
        path: Optional path to baskets.parquet file. If None, uses default location
              in entityidentity/baskets/data/baskets.parquet

    Returns:
        DataFrame with basket entities and all metadata columns:
          - basket_id: Unique identifier (e.g., "PGM_4E", "BATTERY_PACK")
          - basket_key: Human-readable slug (e.g., "pgm-4e", "battery-pack")
          - name, name_norm: Display and normalized names
          - description: Brief description of basket and uses
          - alias1...alias10: Common aliases
          - component1...component10: Constituent metals/materials

    Examples:
        >>> df = load_baskets()
        >>> df[['name', 'basket_id', 'description']].head()
    """
    if path is None:
        # Use shared utility to find data file (baskets data is in baskets/data/)
        found_path = find_data_file(
            module_file=__file__,
            subdirectory="baskets",
            filenames=["baskets.parquet"],
            search_dev_tables=False,  # Baskets data only in package, not tables/
            module_local_data=True,  # Check baskets/data/ directory
        )

        if found_path is None:
            # Generate helpful error message
            baskets_dir = Path(__file__).parent / "data"
            error_msg = format_not_found_error(
                subdirectory="baskets",
                searched_locations=[
                    ("Module-local data", baskets_dir),
                ],
                fix_instructions=[
                    "Run entityidentity/baskets/data/build_baskets.py to generate it.",
                ],
            )
            raise FileNotFoundError(error_msg)

        path = found_path

    # Load data using shared utility
    return load_parquet_or_csv(Path(path))


def basket_identifier(
    name: str,
    *,
    threshold: int = 90,
) -> Optional[dict]:
    """Return canonical basket row as dict or None.

    Resolves basket names and aliases to canonical basket entities
    using a multi-stage blocking and fuzzy matching pipeline.

    Resolution strategy:
      1. Exact basket_id match (if query looks like an ID)
      2. Name prefix blocking (first 3 chars normalized)
      3. Final scoring via RapidFuzz WRatio on names + aliases

    Args:
        name: Basket name or alias
              Examples: "PGM 4E", "4e pgm", "NdPr", "Battery Pack", "battery metals"
        threshold: Minimum fuzzy match score (0-100). Default 90.

    Returns:
        Dict with canonical basket fields, or None if no match above threshold.
        Dict contains: basket_id, basket_key, name, description, aliases, components.

    Examples:
        >>> basket_identifier("PGM 4E")
        {'basket_id': 'PGM_4E', 'name': 'PGM 4E', 'component1': 'Pt', ...}

        >>> basket_identifier("4e pgm")
        {'basket_id': 'PGM_4E', 'name': 'PGM 4E', ...}

        >>> basket_identifier("ndpr")
        {'basket_id': 'NDPR', 'name': 'NdPr', ...}

        >>> basket_identifier("battery metals")
        {'basket_id': 'BATTERY_PACK', 'name': 'Battery Pack', ...}
    """
    df = load_baskets()
    result = _resolve_basket(
        name=name,
        df=df,
        threshold=threshold,
    )

    if result is None:
        return None

    # Convert Series to dict
    return result.to_dict()


def match_basket(name: str, *, k: int = 5) -> list[dict]:
    """Top-K candidates + scores (for review UIs).

    Returns the top K basket candidates with their fuzzy match scores,
    useful for interactive review interfaces, disambiguation, and
    understanding resolution decisions.

    Args:
        name: Basket name or alias to match
        k: Number of top candidates to return. Default 5.

    Returns:
        List of dicts, each containing:
          - All basket fields (basket_id, name, components, etc.)
          - score: Fuzzy match score (0-100)
        Ordered by descending score.

    Examples:
        >>> matches = match_basket("pgm", k=3)
        >>> for m in matches:
        ...     print(f"{m['name']} ({m['basket_id']}) - score: {m['score']}")
        PGM 4E (PGM_4E) - score: 95
        PGM 5E (PGM_5E) - score: 95
        ...
    """
    df = load_baskets()
    results = _topk_matches(name=name, df=df, k=k)

    # Convert list of (Series, score) tuples to list of dicts with scores
    return [
        {**row.to_dict(), "score": score}
        for row, score in results
    ]


def list_baskets() -> pd.DataFrame:
    """List all baskets.

    Returns the full baskets DataFrame. Useful for exploring
    available baskets and their components.

    Returns:
        DataFrame with all basket entities

    Examples:
        >>> baskets_df = list_baskets()
        >>> baskets_df[['name', 'basket_id']].values
        array([['PGM 4E', 'PGM_4E'], ['PGM 5E', 'PGM_5E'], ...])
    """
    return load_baskets()


def get_basket_components(name: str, *, threshold: int = 90) -> Optional[list[str]]:
    """Get list of component symbols for a basket.

    Convenience function that resolves a basket and returns just the component symbols.

    Args:
        name: Basket name or alias
        threshold: Minimum fuzzy match score (0-100). Default 90.

    Returns:
        List of component symbols (e.g., ["Pt", "Pd", "Rh", "Au"]),
        or None if basket not found.

    Examples:
        >>> get_basket_components("PGM 4E")
        ['Pt', 'Pd', 'Rh', 'Au']

        >>> get_basket_components("NdPr")
        ['Nd', 'Pr']

        >>> get_basket_components("Battery Pack")
        ['Li', 'Co', 'Ni', 'Mn', 'C']
    """
    basket = basket_identifier(name, threshold=threshold)
    if basket is None:
        return None

    # Extract component symbols from component1...component10 columns
    components = []
    for i in range(1, 11):
        comp_col = f"component{i}"
        if comp_col in basket and basket[comp_col]:
            # Component format is either "symbol" or "symbol:weight_pct"
            comp_str = basket[comp_col]
            # Extract just the symbol part (before colon if present)
            symbol = comp_str.split(":")[0] if ":" in comp_str else comp_str
            if symbol:
                components.append(symbol)

    return components if components else None


__all__ = [
    "load_baskets",
    "basket_identifier",
    "match_basket",
    "list_baskets",
    "get_basket_components",
]
