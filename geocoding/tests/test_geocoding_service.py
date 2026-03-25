from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from geocoding.client import GoogleMapsClient
from geocoding.models import GeocodeLookup
from geocoding.services import GeocodingResult, GeocodingService


SAMPLE_GOOGLE_RESPONSE = {
    "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
    "geometry": {"location": {"lat": 34.07642, "lng": -118.37602}},
    "place_id": "ChIJMyzlkPa4woARkNMBOsEcCBQ",
    "address_components": {"locality": "Los Angeles"},
}

SAMPLE_REVERSE_RESPONSE = {
    "formatted_address": "277 Bedford Ave, Brooklyn, NY 11211, USA",
    "geometry": {"location": {"lat": 40.714224, "lng": -73.961452}},
    "place_id": "ChIJd8BlQ2BZwokRAFUEcm_qrcA",
    "address_components": {"locality": "Brooklyn"},
}


def _make_service() -> tuple[GeocodingService, MagicMock]:
    mock_client = MagicMock(spec=GoogleMapsClient)
    return GeocodingService(mock_client), mock_client


@pytest.mark.django_db
class TestForwardGeocodeService:

    def test_cache_miss_calls_google_and_persists(self):
        service, mock_client = _make_service()
        mock_client.geocode.return_value = SAMPLE_GOOGLE_RESPONSE

        result = service.geocode("Beverly Centre")

        mock_client.geocode.assert_called_once_with("beverly centre")
        assert isinstance(result, GeocodingResult)
        assert result.formatted_address == SAMPLE_GOOGLE_RESPONSE["formatted_address"]
        assert result.latitude == Decimal("34.07642")
        assert result.longitude == Decimal("-118.37602")
        assert result.place_id == "ChIJMyzlkPa4woARkNMBOsEcCBQ"

        # Verify DB persistence
        lookup = GeocodeLookup.objects.get(
            normalized_query="beverly centre", lookup_type="forward"
        )
        assert lookup.formatted_address == result.formatted_address

    def test_cache_hit_skips_google(self):
        service, mock_client = _make_service()

        # Seed the database with a prior lookup
        GeocodeLookup.objects.create(
            normalized_query="beverly centre",
            formatted_address="Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
            latitude=Decimal("34.0764200"),
            longitude=Decimal("-118.3760200"),
            place_id="ChIJMyzlkPa4woARkNMBOsEcCBQ",
            address_components={"locality": "Los Angeles"},
            lookup_type="forward",
        )

        result = service.geocode("  Beverly   Centre  ")

        mock_client.geocode.assert_not_called()
        assert result.formatted_address.startswith("Beverly Center")
        assert result.place_id == "ChIJMyzlkPa4woARkNMBOsEcCBQ"

    def test_duplicate_calls_do_not_create_duplicate_records(self):
        service, mock_client = _make_service()
        mock_client.geocode.return_value = SAMPLE_GOOGLE_RESPONSE

        service.geocode("Beverly Centre")
        service.geocode("  beverly   centre  ")
        service.geocode("BEVERLY CENTRE")

        assert (
            GeocodeLookup.objects.filter(
                normalized_query="beverly centre", lookup_type="forward"
            ).count()
            == 1
        )
        # Only the first call should hit Google
        mock_client.geocode.assert_called_once()


@pytest.mark.django_db
class TestReverseGeocodeService:

    def test_cache_miss_calls_google_and_persists(self):
        service, mock_client = _make_service()
        mock_client.reverse_geocode.return_value = SAMPLE_REVERSE_RESPONSE

        result = service.reverse_geocode(Decimal("40.7142240"), Decimal("-73.9614520"))

        mock_client.reverse_geocode.assert_called_once_with(40.714224, -73.961452)
        assert result.formatted_address == SAMPLE_REVERSE_RESPONSE["formatted_address"]
        assert result.place_id == "ChIJd8BlQ2BZwokRAFUEcm_qrcA"

        lookup = GeocodeLookup.objects.get(
            latitude=Decimal("40.7142240"),
            longitude=Decimal("-73.9614520"),
            lookup_type="reverse",
        )
        assert lookup.place_id == result.place_id

    def test_cache_hit_skips_google(self):
        service, mock_client = _make_service()

        GeocodeLookup.objects.create(
            normalized_query="40.7142240,-73.9614520",
            formatted_address="277 Bedford Ave, Brooklyn, NY 11211, USA",
            latitude=Decimal("40.7142240"),
            longitude=Decimal("-73.9614520"),
            place_id="ChIJd8BlQ2BZwokRAFUEcm_qrcA",
            address_components={"locality": "Brooklyn"},
            lookup_type="reverse",
        )

        result = service.reverse_geocode(Decimal("40.7142240"), Decimal("-73.9614520"))

        mock_client.reverse_geocode.assert_not_called()
        assert result.formatted_address == "277 Bedford Ave, Brooklyn, NY 11211, USA"


def _whitespace_variants(base: str) -> st.SearchStrategy[str]:
    return st.tuples(
        st.sampled_from(["", " ", "  ", "\t", "\n"]),  # leading ws
        st.sampled_from([base, base.upper(), base.title(), base.swapcase()]),
        st.sampled_from(["", " ", "  ", "\t", "\n"]),  # trailing ws
    ).map(lambda t: t[0] + t[1] + t[2])


@pytest.mark.django_db
class TestLookupDeduplicationProperty:

    @given(
        variants=st.lists(
            _whitespace_variants("beverly centre"),
            min_size=2,
            max_size=6,
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_forward_geocode_deduplication(self, variants):
        GeocodeLookup.objects.filter(
            normalized_query="beverly centre", lookup_type="forward"
        ).delete()

        service, mock_client = _make_service()
        mock_client.geocode.return_value = SAMPLE_GOOGLE_RESPONSE

        for addr in variants:
            service.geocode(addr)

        count = GeocodeLookup.objects.filter(
            normalized_query="beverly centre", lookup_type="forward"
        ).count()
        assert count == 1, (
            f"Expected 1 record but found {count} for variants: {variants}"
        )
