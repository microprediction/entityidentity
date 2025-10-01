"""
Robust Country Entity Resolution
--------------------------------

Primary pipeline:
  1) country_converter (coco) direct conversion (handles lots of aliases)
  2) pycountry lookup (exact, official ISO 3166)
  3) rapidfuzz fuzzy match over expanded alias table (incl. common colloquialisms)

API:
  country_identifier(name, to='ISO2', allow_user_assigned=True, fuzzy=True, fuzzy_threshold=85)
  country_identifiers(names, to='ISO2', allow_user_assigned=True, fuzzy=True, fuzzy_threshold=85)

Examples:
  >>> country_identifier("USA")            # 'US'
  >>> country_identifier("Deutschland")    # 'DE'
  >>> country_identifier("Ivory Coast")    # 'CI'
  >>> country_identifier("England")        # 'GB'
  >>> country_identifiers(["México", "Holland"], to="ISO3")  # ['MEX', 'NLD']
"""

from __future__ import annotations
from typing import Iterable, List, Optional, Dict, Tuple

# ---- Optional imports with helpful error messages ----
try:
    import country_converter as coco
except ImportError as e:
    raise ImportError("country_converter not installed. pip install country_converter") from e

try:
    import pycountry
except ImportError as e:
    raise ImportError("pycountry not installed. pip install pycountry") from e

try:
    from rapidfuzz import process, fuzz
except ImportError as e:
    raise ImportError("rapidfuzz not installed. pip install rapidfuzz") from e


# ---- Helpers: canonicalization and alias expansion ----
def _norm(s: str) -> str:
    return s.strip().lower().replace("’", "'")


def _pycountry_catalog() -> Dict[str, Dict[str, str]]:
    """
    Build a catalog keyed by many name variants -> canonical ISO2/ISO3/numeric.
    Returns dict: name_variant_lower -> {'ISO2': 'US', 'ISO3': 'USA', 'numeric': '840'}
    """
    catalog: Dict[str, Dict[str, str]] = {}

    def put(name: Optional[str], alpha2: str, alpha3: str, numeric: str):
        if not name:
            return
        catalog[_norm(name)] = {"ISO2": alpha2, "ISO3": alpha3, "numeric": numeric}

    for c in pycountry.countries:
        alpha2 = getattr(c, "alpha_2", None)
        alpha3 = getattr(c, "alpha_3", None)
        numeric = getattr(c, "numeric", None)
        if not (alpha2 and alpha3 and numeric):
            continue

        # Primary names
        put(getattr(c, "name", None), alpha2, alpha3, numeric)
        # Optional extras
        put(getattr(c, "official_name", None), alpha2, alpha3, numeric)
        put(getattr(c, "common_name", None), alpha2, alpha3, numeric)

        # Some common “Country, The” style alternates
        name = getattr(c, "name", "")
        if ", The" in name:
            put(name.replace(", The", ""), alpha2, alpha3, numeric)

    # Hand-add very common colloquialisms / regions that users expect:
    manual_aliases = {
        "england": "GB",
        "scotland": "GB",
        "wales": "GB",
        "northern ireland": "GB",
        "holland": "NL",
        "ivory coast": "CI",
        "cote d'ivoire": "CI",
        "laos": "LA",
        "moldova": "MD",
        "russia": "RU",
        "south korea": "KR",
        "north korea": "KP",
        "vietnam": "VN",
        "viet nam": "VN",
        "syria": "SY",
        "palestine": "PS",
        "bolivia": "BO",
        "brunei": "BN",
        "cape verde": "CV",
        "czechia": "CZ",
        "eswatini": "SZ",  # ISO kept SZ (formerly Swaziland)
        "micronesia": "FM",
        "vatican": "VA",
        "venezuela": "VE",
        "uae": "AE",
        "emirates": "AE",
        "myanmar": "MM",
        "burma": "MM",
        "taiwan": "TW",  # ISO: TW (Taiwan, Province of China) wording aside
        # Regions often used as country shorthand in data:
        "kosovo": "XK",  # user-assigned (“XK”); not official ISO
    }

    # Backfill manual aliases via pycountry to get ISO3/numeric
    alpha2_map = {getattr(c, "alpha_2"): c for c in pycountry.countries if hasattr(c, "alpha_2")}
    for alias, a2 in manual_aliases.items():
        if a2 == "XK":
            # Not in pycountry; fill minimally
            catalog[_norm(alias)] = {"ISO2": "XK", "ISO3": "XKX", "numeric": "000"}
            continue
        c = alpha2_map.get(a2)
        if c:
            catalog[_norm(alias)] = {
                "ISO2": c.alpha_2,
                "ISO3": getattr(c, "alpha_3", ""),
                "numeric": getattr(c, "numeric", ""),
            }

    return catalog


# Build one global catalog for fuzzy fallback
_CATALOG = _pycountry_catalog()
_CANDIDATE_NAMES = list(_CATALOG.keys())


# ---- Conversions between code systems ----
def _convert_code_system(alpha2: str, to: str) -> Optional[str]:
    """Given ISO2 code, return in requested code system using pycountry."""
    to = to.upper()
    # Kosovo user-assigned convenience
    if alpha2 == "XK":
        if to == "ISO2":
            return "XK"
        if to == "ISO3":
            return "XKX"
        if to == "NUMERIC":
            return "000"
        return None

    country = next((c for c in pycountry.countries if getattr(c, "alpha_2", None) == alpha2), None)
    if not country:
        return None

    if to == "ISO2":
        return country.alpha_2
    elif to == "ISO3":
        return getattr(country, "alpha_3", None)
    elif to == "NUMERIC" or to == "NUM":
        num = getattr(country, "numeric", None)
        # Ensure leading zeros preserved as string (e.g., '004' for Afghanistan)
        return f"{int(num):03d}" if num is not None else None
    else:
        return None


# ---- Main resolution ----
def country_identifier(
    name: str,
    to: str = "ISO2",
    *,
    allow_user_assigned: bool = True,
    fuzzy: bool = True,
    fuzzy_threshold: int = 85,
) -> Optional[str]:
    """
    Resolve a country-like string to a canonical code.

    Args:
        name: Any country hint: 'USA', 'México', 'England', 'Ivory Coast', 'DEU'
        to:   'ISO2' (default), 'ISO3', or 'numeric'
        allow_user_assigned: allow 'XK' (Kosovo) mapping
        fuzzy: use fuzzy fallback on last resort
        fuzzy_threshold: minimum RapidFuzz score to accept a fuzzy match

    Returns:
        Canonical code in requested system, or None if not recognized.
    """
    if not name or not str(name).strip():
        return None

    target = to.upper()
    s = str(name).strip()

    # 1) Try country_converter (handles tons of aliases out of the box)
    cc = coco.CountryConverter()

    # Direct: try interpreting as code first (helps speed & determinism)
    direct = cc.convert(names=[s], to="ISO2", not_found=None)
    a2 = direct[0] if isinstance(direct, list) else direct
    if a2 and a2 != "not found":
        # Optionally exclude XK here (coco may not return XK anyway)
        if a2 == "XK" and not allow_user_assigned:
            pass
        else:
            out = _convert_code_system(a2, target)
            if out:
                return out

    # Name-based conversion (coco already supports many variants)
    by_name = cc.convert(names=[s], to="ISO2", not_found=None)
    a2 = by_name[0] if isinstance(by_name, list) else by_name
    if a2 and a2 != "not found":
        if a2 == "XK" and not allow_user_assigned:
            pass
        else:
            out = _convert_code_system(a2, target)
            if out:
                return out

    # 2) pycountry exact lookup (works for 'USA', 'DEU', official names)
    try:
        c = pycountry.countries.lookup(s)
        a2 = getattr(c, "alpha_2", None)
        if a2:
            if a2 == "XK" and not allow_user_assigned:
                pass
            else:
                out = _convert_code_system(a2, target)
                if out:
                    return out
    except LookupError:
        pass

    # 3) Explicit manual alias quick check (fast path before fuzzy)
    alias_hit = _CATALOG.get(_norm(s))
    if alias_hit:
        if alias_hit["ISO2"] == "XK" and not allow_user_assigned:
            pass
        else:
            return alias_hit[target] if target in alias_hit else None

    # 4) Fuzzy fallback over expanded alias table
    if fuzzy:
        match = process.extractOne(_norm(s), _CANDIDATE_NAMES, scorer=fuzz.WRatio)
        if match:
            best_name, score, _ = match
            if score >= fuzzy_threshold:
                mapped = _CATALOG.get(best_name)
                if mapped:
                    if mapped["ISO2"] == "XK" and not allow_user_assigned:
                        return None
                    return mapped[target]

    return None


def country_identifiers(
    names: Iterable[str],
    to: str = "ISO2",
    *,
    allow_user_assigned: bool = True,
    fuzzy: bool = True,
    fuzzy_threshold: int = 85,
) -> List[Optional[str]]:
    """Vectorized convenience wrapper."""
    return [
        country_identifier(
            n, to=to, allow_user_assigned=allow_user_assigned, fuzzy=fuzzy, fuzzy_threshold=fuzzy_threshold
        )
        for n in names
    ]


# ---- If you want a tiny CLI smoke test ----
if __name__ == "__main__":
    tests = [
        "USA", "United States", "America", "México", "Holland",
        "Ivory Coast", "Côte d'Ivoire", "Deutschland", "England",
        "Untied States", "Korea, Republic of", "Viet Nam", "Kosovo"
    ]
    print({t: country_identifier(t) for t in tests})
