"""Facility linking and resolution module - stub implementation."""

import os
import math
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from difflib import SequenceMatcher

from entityidentity import match_company


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.

    Args:
        lat1, lon1: Latitude and longitude of first point in decimal degrees
        lat2, lon2: Latitude and longitude of second point in decimal degrees

    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in kilometers
    r = 6371

    return r * c


def _score_name_match(name1: str, name2: str) -> float:
    """Score similarity between two facility names."""
    if not name1 or not name2:
        return 0.0

    # Normalize for comparison
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    if n1 == n2:
        return 1.0

    # Use sequence matcher for fuzzy matching
    return SequenceMatcher(None, n1, n2).ratio()


def _score_geo_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Score based on geographic distance."""
    dist_km = haversine_distance(lat1, lon1, lat2, lon2)

    # Scoring function: exponential decay
    # Perfect match at 0 km, ~0.9 at 10 km, 0.5 at ~50 km, near 0 at 500+ km
    # Using decay constant of 100 for gentler decay
    return math.exp(-dist_km / 100)


def _score_company_match(company_id1: Optional[str], company_id2: Optional[str]) -> float:
    """Score company match."""
    if not company_id1 or not company_id2:
        return 0.0
    return 1.0 if company_id1 == company_id2 else 0.0


class FacilityLinker:
    """Links facilities to companies using fuzzy matching."""

    def __init__(self, facilities_path: Optional[str] = None):
        """
        Initialize facility linker.

        Args:
            facilities_path: Path to facilities master data file
        """
        if facilities_path is None:
            facilities_path = os.getenv("ENTITYIDENTITY_FACILITIES_PATH", "/nonexistent")

        self.facilities_df = None
        self.company_resolver = match_company

        # Try to load facilities data
        if os.path.exists(facilities_path):
            try:
                self.facilities_df = pd.read_parquet(facilities_path)
            except Exception as e:
                print(f"Warning: Could not load facilities data: {e}")
                self.facilities_df = None

    def link(
        self,
        facility_name: Optional[str] = None,
        company_hint: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        threshold: float = 0.5,
        return_features: bool = False
    ) -> Dict[str, Any]:
        """
        Link a facility to company.

        Args:
            facility_name: Name of the facility
            company_hint: Company name or ID hint
            latitude, longitude: Geographic coordinates
            threshold: Minimum confidence score
            return_features: Whether to return feature scores

        Returns:
            Dictionary with facility_id, company_id, link_score, etc.
        """
        result = {
            'facility_id': None,
            'company_id': None,
            'facility_name': None,
            'company_name': None,
            'link_score': 0
        }

        # Try to resolve company if hint provided
        if company_hint:
            try:
                company_result = self.company_resolver(company_hint)
                if company_result:
                    # Use wikidata_qid or lei as the company ID, or create one from name and country
                    company_id = company_result.get('wikidata_qid') or company_result.get('lei')
                    if not company_id and company_result.get('name'):
                        # Create ID from name and country
                        country = company_result.get('country', '')
                        company_id = f"{company_result['name']}:{country}" if country else company_result['name']
                    result['company_id'] = company_id
                    result['company_name'] = company_result.get('name')
            except Exception:
                pass

        # If no facilities data, return stub result
        if self.facilities_df is None:
            if return_features:
                result['features'] = {
                    'name_score': 0,
                    'geo_score': 0,
                    'company_score': 0
                }
            return result

        # TODO: Implement full blocking and scoring when facilities data available
        # This would include:
        # 1. Block candidates by company, geo region, name tokens
        # 2. Score each candidate
        # 3. Return best match above threshold

        # For now, return stub result
        if return_features:
            result['features'] = {
                'name_score': 0,
                'geo_score': 0,
                'company_score': 0
            }

        return result


def link_facility(
    facility_name: Optional[str] = None,
    company_hint: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    threshold: float = 0.5,
    return_features: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to link a facility.

    Args:
        facility_name: Name of the facility
        company_hint: Company name or ID hint
        latitude, longitude: Geographic coordinates
        threshold: Minimum confidence score
        return_features: Whether to return feature scores

    Returns:
        Dictionary with facility_id, company_id, link_score, etc.
    """
    # Validate coordinates if provided
    if latitude is not None:
        if not isinstance(latitude, (int, float)):
            raise TypeError(f"latitude must be numeric, got {type(latitude)}")
        if not -90 <= latitude <= 90:
            latitude = max(-90, min(90, latitude))  # Clamp to valid range

    if longitude is not None:
        if not isinstance(longitude, (int, float)):
            raise TypeError(f"longitude must be numeric, got {type(longitude)}")
        if not -180 <= longitude <= 180:
            longitude = max(-180, min(180, longitude))  # Clamp to valid range

    linker = FacilityLinker()
    return linker.link(
        facility_name=facility_name,
        company_hint=company_hint,
        latitude=latitude,
        longitude=longitude,
        threshold=threshold,
        return_features=return_features
    )