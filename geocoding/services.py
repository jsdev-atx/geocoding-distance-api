import math
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geocoding.client import GoogleMapsClient


@dataclass(frozen=True)
class DistanceResult:
    origin_lat: Decimal
    origin_lng: Decimal
    destination_lat: Decimal
    destination_lng: Decimal
    distance_km: float
    distance_miles: float


class DistanceCalculator:
    """Haversine great-circle distance between two points on Earth."""

    EARTH_RADIUS_KM = 6371.0
    KM_TO_MILES = 0.621371

    @staticmethod
    def calculate(
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> DistanceResult:
        for name, val, lo, hi in [
            ("origin_lat", origin_lat, -90, 90),
            ("dest_lat", dest_lat, -90, 90),
            ("origin_lng", origin_lng, -180, 180),
            ("dest_lng", dest_lng, -180, 180),
        ]:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise ValueError(f"{name} must be a finite number.")
            if val < lo or val > hi:
                raise ValueError(f"{name} must be between {lo} and {hi}.")

        lat1 = math.radians(origin_lat)
        lng1 = math.radians(origin_lng)
        lat2 = math.radians(dest_lat)
        lng2 = math.radians(dest_lng)

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance_km = DistanceCalculator.EARTH_RADIUS_KM * c
        distance_miles = distance_km * DistanceCalculator.KM_TO_MILES

        return DistanceResult(
            origin_lat=Decimal(str(origin_lat)),
            origin_lng=Decimal(str(origin_lng)),
            destination_lat=Decimal(str(dest_lat)),
            destination_lng=Decimal(str(dest_lng)),
            distance_km=round(distance_km, 4),
            distance_miles=round(distance_miles, 4),
        )


def _normalize_query(query: str) -> str:
    """Lowercase, strip, and collapse whitespace. Raises ValueError if empty."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string.")
    stripped = query.strip().lower()
    return re.sub(r"\s+", " ", stripped)


@dataclass(frozen=True)
class GeocodingResult:
    formatted_address: str
    latitude: Decimal
    longitude: Decimal
    place_id: str
    address_components: dict


class GeocodingService:
    """Checks DB for prior lookups before hitting Google. Persists new results."""

    def __init__(self, google_client: "GoogleMapsClient"):
        self._google = google_client

    def geocode(self, address: str) -> GeocodingResult:
        """Forward geocode with DB-backed deduplication."""
        from geocoding.models import GeocodeLookup

        normalized = _normalize_query(address)
        existing = GeocodeLookup.objects.filter(
            normalized_query=normalized, lookup_type="forward"
        ).first()
        if existing:
            return self._to_result(existing)

        raw = self._google.geocode(normalized)
        result = self._parse_google_response(raw)
        self._persist_lookup(normalized, result, lookup_type="forward")
        return result

    def reverse_geocode(self, lat: Decimal, lng: Decimal) -> GeocodingResult:
        """Reverse geocode with DB-backed deduplication."""
        from geocoding.models import GeocodeLookup

        existing = GeocodeLookup.objects.filter(
            latitude=lat, longitude=lng, lookup_type="reverse"
        ).first()
        if existing:
            return self._to_result(existing)

        raw = self._google.reverse_geocode(float(lat), float(lng))
        result = self._parse_google_response(raw)
        self._persist_lookup(f"{lat},{lng}", result, lookup_type="reverse")
        return result

    @staticmethod
    def _parse_google_response(raw: dict) -> GeocodingResult:
        location = raw["geometry"]["location"]
        return GeocodingResult(
            formatted_address=raw["formatted_address"],
            latitude=Decimal(str(location["lat"])),
            longitude=Decimal(str(location["lng"])),
            place_id=raw["place_id"],
            address_components=raw.get("address_components", {}),
        )

    @staticmethod
    def _persist_lookup(
        normalized_query: str, result: GeocodingResult, lookup_type: str
    ) -> None:
        from geocoding.models import GeocodeLookup

        GeocodeLookup.objects.create(
            normalized_query=normalized_query,
            formatted_address=result.formatted_address,
            latitude=result.latitude,
            longitude=result.longitude,
            place_id=result.place_id,
            address_components=result.address_components,
            lookup_type=lookup_type,
        )

    @staticmethod
    def _to_result(lookup) -> GeocodingResult:
        return GeocodingResult(
            formatted_address=lookup.formatted_address,
            latitude=lookup.latitude,
            longitude=lookup.longitude,
            place_id=lookup.place_id,
            address_components=lookup.address_components,
        )
