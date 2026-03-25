from unittest.mock import MagicMock, patch

import pytest
import requests

from geocoding.client import GoogleMapsClient
from geocoding.exceptions import GeocodingError, RateLimitError, UpstreamError


@pytest.fixture
def client():
    return GoogleMapsClient(api_key="test-key", timeout=5)


def _ok_response(result=None):
    if result is None:
        result = {
            "formatted_address": "123 Main St",
            "geometry": {"location": {"lat": 34.0, "lng": -118.0}},
            "place_id": "ChIJ_test",
        }
    resp = MagicMock()
    resp.json.return_value = {"status": "OK", "results": [result]}
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status):
    resp = MagicMock()
    resp.json.return_value = {"status": status, "results": []}
    resp.raise_for_status = MagicMock()
    return resp


class TestGeocode:

    def test_success(self, client):
        with patch.object(client._session, "get", return_value=_ok_response()):
            result = client.geocode("123 Main St")
            assert result["place_id"] == "ChIJ_test"

    def test_zero_results(self, client):
        with patch.object(client._session, "get", return_value=_error_response("ZERO_RESULTS")):
            with pytest.raises(GeocodingError, match="ZERO_RESULTS"):
                client.geocode("nonexistent place")


class TestReverseGeocode:

    def test_success(self, client):
        with patch.object(client._session, "get", return_value=_ok_response()):
            result = client.reverse_geocode(34.0, -118.0)
            assert result["place_id"] == "ChIJ_test"


class TestRetryAndErrors:

    @patch("geocoding.client.time.sleep")
    def test_retries_then_succeeds(self, mock_sleep, client):
        responses = [_error_response("OVER_QUERY_LIMIT"), _error_response("OVER_QUERY_LIMIT"), _ok_response()]
        with patch.object(client._session, "get", side_effect=responses):
            result = client.geocode("123 Main St")
            assert result["place_id"] == "ChIJ_test"
            assert mock_sleep.call_count == 2

    @patch("geocoding.client.time.sleep")
    def test_rate_limit_after_max_retries(self, mock_sleep, client):
        with patch.object(client._session, "get", side_effect=[_error_response("OVER_QUERY_LIMIT")] * 4):
            with pytest.raises(RateLimitError):
                client.geocode("123 Main St")

    def test_connection_error(self, client):
        with patch.object(client._session, "get", side_effect=requests.ConnectionError):
            with pytest.raises(UpstreamError):
                client.geocode("123 Main St")

    def test_timeout(self, client):
        with patch.object(client._session, "get", side_effect=requests.Timeout):
            with pytest.raises(UpstreamError):
                client.geocode("123 Main St")
