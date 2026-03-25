import pytest
from django.test import override_settings
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient

out_of_range_latitudes = (
    st.floats(min_value=90.001, max_value=1000)
    | st.floats(min_value=-1000, max_value=-90.001)
)

out_of_range_longitudes = (
    st.floats(min_value=180.001, max_value=1000)
    | st.floats(min_value=-1000, max_value=-180.001)
)

valid_latitudes = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
valid_longitudes = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)

_SUPPRESS = [HealthCheck.function_scoped_fixture]

_NO_THROTTLE = {
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "EXCEPTION_HANDLER": "geocoding.views.custom_exception_handler",
}


@pytest.mark.django_db
class TestReverseGeocodeInvalidLatitude:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(lat=out_of_range_latitudes, lng=valid_longitudes)
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_reverse_geocode_rejects_out_of_range_lat(self, api_client, lat, lng):
        client = APIClient()
        response = client.get(
            "/api/v1/reverse-geocode/",
            {"lat": str(lat), "lng": str(lng)},
        )
        assert response.status_code == 400, (
            f"Expected 400 for lat={lat}, got {response.status_code}"
        )
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
class TestReverseGeocodeInvalidLongitude:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(lat=valid_latitudes, lng=out_of_range_longitudes)
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_reverse_geocode_rejects_out_of_range_lng(self, api_client, lat, lng):
        client = APIClient()
        response = client.get(
            "/api/v1/reverse-geocode/",
            {"lat": str(lat), "lng": str(lng)},
        )
        assert response.status_code == 400, (
            f"Expected 400 for lng={lng}, got {response.status_code}"
        )
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_COORDINATES"


@pytest.mark.django_db
class TestDistanceInvalidCoordinates:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(
        origin_lat=out_of_range_latitudes,
        origin_lng=valid_longitudes,
        dest_lat=valid_latitudes,
        dest_lng=valid_longitudes,
    )
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_distance_rejects_out_of_range_origin_lat(
        self, api_client, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        client = APIClient()
        response = client.get(
            "/api/v1/distance/",
            {
                "origin_lat": str(origin_lat),
                "origin_lng": str(origin_lng),
                "dest_lat": str(dest_lat),
                "dest_lng": str(dest_lng),
            },
        )
        assert response.status_code == 400, (
            f"Expected 400 for origin_lat={origin_lat}, got {response.status_code}"
        )
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_COORDINATES"

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(
        origin_lat=valid_latitudes,
        origin_lng=out_of_range_longitudes,
        dest_lat=valid_latitudes,
        dest_lng=valid_longitudes,
    )
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_distance_rejects_out_of_range_origin_lng(
        self, api_client, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        client = APIClient()
        response = client.get(
            "/api/v1/distance/",
            {
                "origin_lat": str(origin_lat),
                "origin_lng": str(origin_lng),
                "dest_lat": str(dest_lat),
                "dest_lng": str(dest_lng),
            },
        )
        assert response.status_code == 400, (
            f"Expected 400 for origin_lng={origin_lng}, got {response.status_code}"
        )
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_COORDINATES"

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(
        origin_lat=valid_latitudes,
        origin_lng=valid_longitudes,
        dest_lat=out_of_range_latitudes,
        dest_lng=valid_longitudes,
    )
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_distance_rejects_out_of_range_dest_lat(
        self, api_client, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        client = APIClient()
        response = client.get(
            "/api/v1/distance/",
            {
                "origin_lat": str(origin_lat),
                "origin_lng": str(origin_lng),
                "dest_lat": str(dest_lat),
                "dest_lng": str(dest_lng),
            },
        )
        assert response.status_code == 400, (
            f"Expected 400 for dest_lat={dest_lat}, got {response.status_code}"
        )
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_COORDINATES"

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(
        origin_lat=valid_latitudes,
        origin_lng=valid_longitudes,
        dest_lat=valid_latitudes,
        dest_lng=out_of_range_longitudes,
    )
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_distance_rejects_out_of_range_dest_lng(
        self, api_client, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        client = APIClient()
        response = client.get(
            "/api/v1/distance/",
            {
                "origin_lat": str(origin_lat),
                "origin_lng": str(origin_lng),
                "dest_lat": str(dest_lat),
                "dest_lng": str(dest_lng),
            },
        )
        assert response.status_code == 400, (
            f"Expected 400 for dest_lng={dest_lng}, got {response.status_code}"
        )
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_COORDINATES"
