from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from geocoding.exceptions import GeocodingError, UpstreamError
from geocoding.models import DistanceCalculation, GeocodeLookup

_NO_THROTTLE = {
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "EXCEPTION_HANDLER": "geocoding.views.custom_exception_handler",
}

MOCK_GOOGLE_RESULT = {
    "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
    "geometry": {"location": {"lat": 34.07642, "lng": -118.37602}},
    "place_id": "ChIJMyzlkPa4woARkNMBOsEcCBQ",
    "address_components": {"locality": "Los Angeles", "country": "US"},
}

MOCK_REVERSE_RESULT = {
    "formatted_address": "277 Bedford Ave, Brooklyn, NY 11211, USA",
    "geometry": {"location": {"lat": 40.714224, "lng": -73.961452}},
    "place_id": "ChIJd8BlQ2BZwokRAFUEcm_qrcA",
    "address_components": {"locality": "Brooklyn", "country": "US"},
}


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_forward_geocode_success(MockClient, client):
    MockClient.return_value.geocode.return_value = MOCK_GOOGLE_RESULT
    response = client.get("/api/v1/geocode/", {"address": "Beverly Centre"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["place_id"] == MOCK_GOOGLE_RESULT["place_id"]
    assert GeocodeLookup.objects.filter(normalized_query="beverly centre").exists()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_forward_geocode_empty_address(client):
    response = client.get("/api/v1/geocode/", {"address": ""})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_forward_geocode_zero_results(MockClient, client):
    MockClient.return_value.geocode.side_effect = GeocodingError("ZERO_RESULTS")
    response = client.get("/api/v1/geocode/", {"address": "xyznonexistent"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GEOCODE_NOT_FOUND"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_forward_geocode_upstream_error(MockClient, client):
    MockClient.return_value.geocode.side_effect = UpstreamError("unreachable")
    response = client.get("/api/v1/geocode/", {"address": "test"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_reverse_geocode_success(MockClient, client):
    MockClient.return_value.reverse_geocode.return_value = MOCK_REVERSE_RESULT
    response = client.get("/api/v1/reverse-geocode/", {"lat": "40.714224", "lng": "-73.961452"})

    assert response.status_code == 200
    assert response.json()["data"]["place_id"] == MOCK_REVERSE_RESULT["place_id"]


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_reverse_geocode_invalid_coords(client):
    response = client.get("/api/v1/reverse-geocode/", {"lat": "91.0", "lng": "0.0"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_distance_success(client):
    response = client.get("/api/v1/distance/", {
        "origin_lat": "34.0764", "origin_lng": "-118.3760",
        "dest_lat": "40.7128", "dest_lng": "-74.0060",
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["distance"]["kilometers"] > 0
    assert data["distance"]["miles"] > 0
    assert DistanceCalculation.objects.count() == 1


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_distance_invalid_coords(client):
    response = client.get("/api/v1/distance/", {
        "origin_lat": "95.0", "origin_lng": "0", "dest_lat": "0", "dest_lng": "0",
    })
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_database_error_returns_500(MockClient, client):
    from django.db import DatabaseError
    with patch("geocoding.services.GeocodingService.geocode", side_effect=DatabaseError("connection refused")):
        response = client.get("/api/v1/geocode/", {"address": "test"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
