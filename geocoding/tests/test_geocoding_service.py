from decimal import Decimal
from unittest.mock import MagicMock

import pytest

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


def _make_service():
    mock_client = MagicMock(spec=GoogleMapsClient)
    return GeocodingService(mock_client), mock_client


@pytest.mark.django_db
class TestForwardGeocode:

    def test_cache_miss_calls_google_and_persists(self):
        service, mock_client = _make_service()
        mock_client.geocode.return_value = SAMPLE_GOOGLE_RESPONSE

        result = service.geocode("Beverly Centre")

        mock_client.geocode.assert_called_once_with("beverly centre")
        assert isinstance(result, GeocodingResult)
        assert result.place_id == "ChIJMyzlkPa4woARkNMBOsEcCBQ"
        assert GeocodeLookup.objects.filter(normalized_query="beverly centre").exists()

    def test_cache_hit_skips_google(self):
        service, mock_client = _make_service()
        GeocodeLookup.objects.create(
            normalized_query="beverly centre",
            formatted_address="Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
            latitude=Decimal("34.0764200"), longitude=Decimal("-118.3760200"),
            place_id="ChIJMyzlkPa4woARkNMBOsEcCBQ",
            address_components={"locality": "Los Angeles"}, lookup_type="forward",
        )

        result = service.geocode("  Beverly   Centre  ")
        mock_client.geocode.assert_not_called()
        assert result.place_id == "ChIJMyzlkPa4woARkNMBOsEcCBQ"

    def test_deduplication(self):
        service, mock_client = _make_service()
        mock_client.geocode.return_value = SAMPLE_GOOGLE_RESPONSE

        service.geocode("Beverly Centre")
        service.geocode("  beverly   centre  ")
        service.geocode("BEVERLY CENTRE")

        assert GeocodeLookup.objects.filter(normalized_query="beverly centre").count() == 1
        mock_client.geocode.assert_called_once()


@pytest.mark.django_db
class TestReverseGeocode:

    def test_cache_miss_calls_google_and_persists(self):
        service, mock_client = _make_service()
        mock_client.reverse_geocode.return_value = SAMPLE_REVERSE_RESPONSE

        result = service.reverse_geocode(Decimal("40.7142240"), Decimal("-73.9614520"))

        mock_client.reverse_geocode.assert_called_once()
        assert result.place_id == "ChIJd8BlQ2BZwokRAFUEcm_qrcA"
        assert GeocodeLookup.objects.filter(lookup_type="reverse").exists()

    def test_cache_hit_skips_google(self):
        service, mock_client = _make_service()
        GeocodeLookup.objects.create(
            normalized_query="40.7142240,-73.9614520",
            formatted_address="277 Bedford Ave, Brooklyn, NY 11211, USA",
            latitude=Decimal("40.7142240"), longitude=Decimal("-73.9614520"),
            place_id="ChIJd8BlQ2BZwokRAFUEcm_qrcA",
            address_components={"locality": "Brooklyn"}, lookup_type="reverse",
        )

        result = service.reverse_geocode(Decimal("40.7142240"), Decimal("-73.9614520"))
        mock_client.reverse_geocode.assert_not_called()
        assert result.formatted_address == "277 Bedford Ave, Brooklyn, NY 11211, USA"
