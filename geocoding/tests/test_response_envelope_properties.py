import pytest
from django.test import override_settings
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient

valid_latitudes = st.floats(
    min_value=-90, max_value=90, allow_nan=False, allow_infinity=False
)
valid_longitudes = st.floats(
    min_value=-180, max_value=180, allow_nan=False, allow_infinity=False
)

out_of_range_latitudes = (
    st.floats(min_value=90.001, max_value=1000)
    | st.floats(min_value=-1000, max_value=-90.001)
)
out_of_range_longitudes = (
    st.floats(min_value=180.001, max_value=1000)
    | st.floats(min_value=-1000, max_value=-180.001)
)

_SUPPRESS = [HealthCheck.function_scoped_fixture]

_NO_THROTTLE = {
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "EXCEPTION_HANDLER": "geocoding.views.custom_exception_handler",
}


def _assert_success_envelope(body: dict) -> None:
    assert body["status"] == "success"
    assert "data" in body
    assert isinstance(body["data"], dict)


def _assert_error_envelope(body: dict) -> None:
    assert body["status"] == "error"
    assert "error" in body
    error = body["error"]
    assert isinstance(error, dict)
    assert "code" in error
    assert "message" in error
    assert isinstance(error["code"], str)
    assert isinstance(error["message"], str)


@pytest.mark.django_db
class TestSuccessEnvelopeDistance:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(
        origin_lat=valid_latitudes.map(lambda x: round(x, 7)),
        origin_lng=valid_longitudes.map(lambda x: round(x, 7)),
        dest_lat=valid_latitudes.map(lambda x: round(x, 7)),
        dest_lng=valid_longitudes.map(lambda x: round(x, 7)),
    )
    @settings(max_examples=30, suppress_health_check=_SUPPRESS, deadline=None)
    def test_distance_success_envelope(
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
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.json()}"
        )
        _assert_success_envelope(response.json())


@pytest.mark.django_db
class TestErrorEnvelopeDistanceInvalidCoords:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(
        origin_lat=out_of_range_latitudes,
        origin_lng=valid_longitudes,
        dest_lat=valid_latitudes,
        dest_lng=valid_longitudes,
    )
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_distance_error_envelope_bad_origin_lat(
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
        assert response.status_code == 400
        _assert_error_envelope(response.json())


@pytest.mark.django_db
class TestErrorEnvelopeGeocodeEmptyAddress:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(address=st.just(""))
    @settings(max_examples=5, suppress_health_check=_SUPPRESS, deadline=None)
    def test_geocode_error_envelope_empty_address(self, api_client, address):
        client = APIClient()
        response = client.get("/api/v1/geocode/", {"address": address})
        assert response.status_code == 400
        _assert_error_envelope(response.json())

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @settings(max_examples=5, suppress_health_check=_SUPPRESS, deadline=None)
    @given(data=st.data())
    def test_geocode_error_envelope_missing_address(self, api_client, data):
        client = APIClient()
        response = client.get("/api/v1/geocode/")
        assert response.status_code == 400
        _assert_error_envelope(response.json())


@pytest.mark.django_db
class TestErrorEnvelopeReverseGeocodeInvalidCoords:

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(lat=out_of_range_latitudes, lng=valid_longitudes)
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_reverse_geocode_error_envelope_bad_lat(self, api_client, lat, lng):
        client = APIClient()
        response = client.get(
            "/api/v1/reverse-geocode/",
            {"lat": str(lat), "lng": str(lng)},
        )
        assert response.status_code == 400
        _assert_error_envelope(response.json())

    @override_settings(REST_FRAMEWORK=_NO_THROTTLE)
    @given(lat=valid_latitudes, lng=out_of_range_longitudes)
    @settings(max_examples=20, suppress_health_check=_SUPPRESS, deadline=None)
    def test_reverse_geocode_error_envelope_bad_lng(self, api_client, lat, lng):
        client = APIClient()
        response = client.get(
            "/api/v1/reverse-geocode/",
            {"lat": str(lat), "lng": str(lng)},
        )
        assert response.status_code == 400
        _assert_error_envelope(response.json())
