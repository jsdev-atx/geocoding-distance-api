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
    mock_instance = MockClient.return_value
    mock_instance.geocode.return_value = MOCK_GOOGLE_RESULT

    response = client.get("/api/v1/geocode/", {"address": "Beverly Centre"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "data" in body
    data = body["data"]
    assert data["formatted_address"] == MOCK_GOOGLE_RESULT["formatted_address"]
    assert data["place_id"] == MOCK_GOOGLE_RESULT["place_id"]
    assert Decimal(data["latitude"]) == Decimal("34.0764200")
    assert Decimal(data["longitude"]) == Decimal("-118.3760200")
    assert data["address_components"] == MOCK_GOOGLE_RESULT["address_components"]

    assert GeocodeLookup.objects.filter(
        normalized_query="beverly centre", lookup_type="forward"
    ).exists()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_forward_geocode_cache_hit(MockClient, client):
    GeocodeLookup.objects.create(
        normalized_query="beverly centre",
        formatted_address="Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
        latitude=Decimal("34.0764200"),
        longitude=Decimal("-118.3760200"),
        place_id="ChIJMyzlkPa4woARkNMBOsEcCBQ",
        address_components={"locality": "Los Angeles", "country": "US"},
        lookup_type="forward",
    )

    response = client.get("/api/v1/geocode/", {"address": "Beverly Centre"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["place_id"] == "ChIJMyzlkPa4woARkNMBOsEcCBQ"

    mock_instance = MockClient.return_value
    mock_instance.geocode.assert_not_called()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_forward_geocode_empty_address(client):
    response = client.get("/api/v1/geocode/", {"address": ""})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_INPUT"
    assert "message" in body["error"]


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_forward_geocode_missing_address(client):
    response = client.get("/api/v1/geocode/")

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_INPUT"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_forward_geocode_zero_results(MockClient, client):
    mock_instance = MockClient.return_value
    mock_instance.geocode.side_effect = GeocodingError("ZERO_RESULTS")

    response = client.get("/api/v1/geocode/", {"address": "xyznonexistent12345"})

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "GEOCODE_NOT_FOUND"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_forward_geocode_upstream_error(MockClient, client):
    mock_instance = MockClient.return_value
    mock_instance.geocode.side_effect = UpstreamError("Google Maps API unreachable")

    response = client.get("/api/v1/geocode/", {"address": "some address"})

    assert response.status_code == 502
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "UPSTREAM_ERROR"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_reverse_geocode_success(MockClient, client):
    mock_instance = MockClient.return_value
    mock_instance.reverse_geocode.return_value = MOCK_REVERSE_RESULT

    response = client.get(
        "/api/v1/reverse-geocode/", {"lat": "40.714224", "lng": "-73.961452"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["formatted_address"] == MOCK_REVERSE_RESULT["formatted_address"]
    assert data["place_id"] == MOCK_REVERSE_RESULT["place_id"]

    assert GeocodeLookup.objects.filter(lookup_type="reverse").exists()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_reverse_geocode_cache_hit(MockClient, client):
    GeocodeLookup.objects.create(
        normalized_query="40.7142240,-73.9614520",
        formatted_address="277 Bedford Ave, Brooklyn, NY 11211, USA",
        latitude=Decimal("40.7142240"),
        longitude=Decimal("-73.9614520"),
        place_id="ChIJd8BlQ2BZwokRAFUEcm_qrcA",
        address_components={"locality": "Brooklyn", "country": "US"},
        lookup_type="reverse",
    )

    response = client.get(
        "/api/v1/reverse-geocode/", {"lat": "40.7142240", "lng": "-73.9614520"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["place_id"] == "ChIJd8BlQ2BZwokRAFUEcm_qrcA"

    mock_instance = MockClient.return_value
    mock_instance.reverse_geocode.assert_not_called()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_reverse_geocode_out_of_range_lat(client):
    response = client.get(
        "/api/v1/reverse-geocode/", {"lat": "91.0", "lng": "0.0"}
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_reverse_geocode_out_of_range_lng(client):
    response = client.get(
        "/api/v1/reverse-geocode/", {"lat": "0.0", "lng": "181.0"}
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_distance_calculation_success(client):
    response = client.get(
        "/api/v1/distance/",
        {
            "origin_lat": "34.0764",
            "origin_lng": "-118.3760",
            "dest_lat": "40.7128",
            "dest_lng": "-74.0060",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    data = body["data"]

    assert "origin" in data
    assert "destination" in data
    assert "distance" in data
    assert Decimal(str(data["origin"]["latitude"])) == Decimal("34.0764000")
    assert data["distance"]["kilometers"] > 0
    assert data["distance"]["miles"] > 0

    km = data["distance"]["kilometers"]
    miles = data["distance"]["miles"]
    assert abs(miles - km * 0.621371) < 0.01


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_distance_persists_record(client):
    assert DistanceCalculation.objects.count() == 0

    client.get(
        "/api/v1/distance/",
        {
            "origin_lat": "34.0764",
            "origin_lng": "-118.3760",
            "dest_lat": "40.7128",
            "dest_lng": "-74.0060",
        },
    )

    assert DistanceCalculation.objects.count() == 1
    record = DistanceCalculation.objects.first()
    assert record.distance_km > 0
    assert record.distance_miles > 0
    assert float(record.origin_lat) == pytest.approx(34.0764, abs=1e-4)


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_distance_out_of_range_origin_lat(client):
    response = client.get(
        "/api/v1/distance/",
        {
            "origin_lat": "95.0",
            "origin_lng": "0.0",
            "dest_lat": "0.0",
            "dest_lng": "0.0",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
def test_distance_out_of_range_dest_lng(client):
    response = client.get(
        "/api/v1/distance/",
        {
            "origin_lat": "0.0",
            "origin_lng": "0.0",
            "dest_lat": "0.0",
            "dest_lng": "200.0",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
@patch("geocoding.views.GoogleMapsClient")
def test_database_error_returns_internal_error(MockClient, client):
    mock_instance = MockClient.return_value
    mock_instance.geocode.return_value = MOCK_GOOGLE_RESULT

    from django.db import DatabaseError
    with patch("geocoding.services.GeocodingService.geocode", side_effect=DatabaseError("connection refused")):
        response = client.get("/api/v1/geocode/", {"address": "test"})

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INTERNAL_ERROR"
