"""Instruments data loader with GCS and local support.

This module loads ticker reference data from Google Cloud Storage (GCS)
or local files, with automatic fallback handling and computed columns.
"""

import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from entityidentity.utils.dataloader import find_data_file, format_not_found_error
from entityidentity.utils.normalize import normalize_name

logger = logging.getLogger(__name__)


def _compute_instrument_id(source: str, ticker: str) -> str:
    """Compute stable instrument ID from source and ticker.

    Args:
        source: Data source (e.g., "Fastmarkets", "LME")
        ticker: Ticker symbol (e.g., "MB-CO-0005")

    Returns:
        16-character hex hash ID
    """
    # Normalize source and ticker for consistency
    source_norm = normalize_name(source, allowed_chars=r"a-z0-9")
    ticker_norm = normalize_name(ticker, allowed_chars=r"a-z0-9\-_")

    # Create composite key
    composite = f"{source_norm}|{ticker_norm}"

    # Generate SHA1 hash and take first 16 characters
    hash_obj = hashlib.sha1(composite.encode("utf-8"))
    return hash_obj.hexdigest()[:16]


def _load_from_gcs(bucket: str = "gsmc-market-data",
                   blob_name: str = "ticker_references.parquet") -> Optional[pd.DataFrame]:
    """Load ticker references from Google Cloud Storage.

    Args:
        bucket: GCS bucket name
        blob_name: Blob path within bucket

    Returns:
        DataFrame if successful, None if GCS unavailable
    """
    try:
        # Try importing google-cloud-storage
        from google.cloud import storage
        from google.auth.exceptions import DefaultCredentialsError

        # Create GCS client
        try:
            client = storage.Client()
        except DefaultCredentialsError:
            logger.warning("No GCS credentials found, falling back to local")
            return None

        # Get bucket and blob
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(blob_name)

        # Check if blob exists
        if not blob.exists():
            logger.warning(f"GCS blob {bucket}/{blob_name} not found")
            return None

        # Download to temporary file and read
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=True) as tmp:
            blob.download_to_filename(tmp.name)
            df = pd.read_parquet(tmp.name)
            logger.info(f"Loaded {len(df)} instruments from GCS: {bucket}/{blob_name}")
            return df

    except ImportError:
        logger.debug("google-cloud-storage not installed, using local files only")
        return None
    except Exception as e:
        logger.warning(f"GCS loading failed: {e}, falling back to local")
        return None


def _add_computed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns to ticker references DataFrame.

    Adds:
        - instrument_id: Stable hash ID
        - ticker_norm: Normalized ticker for matching
        - name_norm: Normalized name for matching
        - material_id: Resolved metal ID (if available)
        - cluster_id: Metal cluster ID (if available)

    Args:
        df: Raw ticker references DataFrame

    Returns:
        DataFrame with computed columns added
    """
    df = df.copy()

    # Ensure required columns exist
    required = ["Source", "asset_id"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        # Try alternate column names
        if "source" in df.columns and "Source" not in df.columns:
            df["Source"] = df["source"]
        if "ticker" in df.columns and "asset_id" not in df.columns:
            df["asset_id"] = df["ticker"]

        # Check again
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    # Add instrument_id
    df["instrument_id"] = df.apply(
        lambda row: _compute_instrument_id(row["Source"], row["asset_id"]),
        axis=1
    )

    # Add normalized columns for matching
    df["ticker_norm"] = df["asset_id"].apply(
        lambda x: normalize_name(str(x), allowed_chars=r"a-z0-9\-_") if pd.notna(x) else ""
    )

    # Handle various name column possibilities
    name_col = None
    for col in ["Name", "name", "asset_name", "instrument_name", "Description"]:
        if col in df.columns:
            name_col = col
            break

    if name_col:
        df["name_norm"] = df[name_col].apply(
            lambda x: normalize_name(str(x), allowed_chars=r"a-z0-9\s\-/()%") if pd.notna(x) else ""
        )
    else:
        df["name_norm"] = ""

    # Add metal crosswalk if material_hint exists
    if "Metal" in df.columns or "material_hint" in df.columns:
        metal_col = "Metal" if "Metal" in df.columns else "material_hint"

        try:
            from entityidentity.metals.metalapi import metal_identifier

            def resolve_metal(hint):
                """Resolve metal hint to ID and cluster."""
                if pd.isna(hint) or str(hint).strip() == "":
                    return None, None

                try:
                    result = metal_identifier(str(hint), threshold=80)
                    if result:
                        # Extract metal_id and cluster_id
                        metal_id = result.get("metal_id") or result.get("metal_key") or result.get("symbol")
                        cluster_id = result.get("cluster_id")
                        return metal_id, cluster_id
                except Exception as e:
                    logger.debug(f"Could not resolve metal '{hint}': {e}")

                return None, None

            # Apply metal resolution
            metal_results = df[metal_col].apply(resolve_metal)
            df["material_id"] = metal_results.apply(lambda x: x[0] if x else None)
            df["cluster_id"] = metal_results.apply(lambda x: x[1] if x else None)

            logger.info(f"Resolved {df['material_id'].notna().sum()}/{len(df)} metals")

        except ImportError:
            logger.warning("Metal identifier not available, skipping material crosswalk")
            df["material_id"] = None
            df["cluster_id"] = None
    else:
        df["material_id"] = None
        df["cluster_id"] = None

    return df


@lru_cache(maxsize=1)
def load_instruments(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load ticker references with automatic GCS/local fallback.

    Loading priority:
    1. Explicit path if provided
    2. GSMC_TICKERS_PATH environment variable
    3. GCS: gs://gsmc-market-data/ticker_references.parquet
    4. Local package data (instruments/data/)
    5. Development tables (../tables/instruments/)

    Args:
        path: Optional explicit path to ticker references file

    Returns:
        DataFrame with ticker references and computed columns

    Raises:
        FileNotFoundError: If no data source is available
    """
    df = None

    # 1. Check explicit path
    if path is not None:
        path = Path(path)
        if path.exists():
            df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
            logger.info(f"Loaded {len(df)} instruments from explicit path: {path}")

    # 2. Check environment variable
    if df is None:
        env_path = os.environ.get("GSMC_TICKERS_PATH")
        if env_path:
            env_path = Path(env_path)
            if env_path.exists():
                df = pd.read_parquet(env_path) if env_path.suffix == ".parquet" else pd.read_csv(env_path)
                logger.info(f"Loaded {len(df)} instruments from GSMC_TICKERS_PATH: {env_path}")

    # 3. Try GCS
    if df is None:
        df = _load_from_gcs()

    # 4. Try local package/development data
    if df is None:
        found_path = find_data_file(
            module_file=__file__,
            subdirectory="instruments",
            filenames=["ticker_references.parquet", "ticker_reference.parquet", "instruments.parquet"],
            search_dev_tables=True,  # Check ../tables/instruments/
            module_local_data=True,  # Check instruments/data/
        )

        if found_path:
            df = pd.read_parquet(found_path) if found_path.suffix == ".parquet" else pd.read_csv(found_path)
            logger.info(f"Loaded {len(df)} instruments from local: {found_path}")

    # If still no data, raise error
    if df is None:
        error_msg = format_not_found_error(
            subdirectory="instruments",
            searched_locations=[
                ("Explicit path", path if path else "Not provided"),
                ("Environment variable", os.environ.get("GSMC_TICKERS_PATH", "Not set")),
                ("Google Cloud Storage", "gs://gsmc-market-data/ticker_references.parquet"),
                ("Package data", Path(__file__).parent / "data"),
                ("Development tables", Path(__file__).parent.parent.parent / "tables" / "instruments"),
            ],
            fix_instructions=[
                "Set GSMC_TICKERS_PATH environment variable to point to local file",
                "Or ensure GCS credentials are configured for gs://gsmc-market-data access",
                "Or place ticker_references.parquet in entityidentity/instruments/data/",
            ],
        )
        raise FileNotFoundError(error_msg)

    # Add computed columns
    df = _add_computed_columns(df)

    return df


def clear_cache():
    """Clear the LRU cache for load_instruments.

    Useful for testing or when data needs to be reloaded.
    """
    load_instruments.cache_clear()
    logger.info("Cleared instruments loader cache")