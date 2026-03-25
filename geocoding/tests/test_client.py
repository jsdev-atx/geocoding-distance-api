from unittest.mock import MagicMock, patch

import pytest
import requests

from geocoding.client import GoogleMapsClient
from geocoding.exceptions import GeocodingError, RateLimitError, UpstreamError


@pytest.fixture
def client():
    return GoogleMapsClient(api_key="test-key", timeout=5)


def _ok_response(result=None):
    """Build a mock response with status OK."""
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
    """Build a mock response with a given Google API status."""
    resp = MagicMock()
    resp.json.return_value = {"status": status, "results": []}
    resp.raise_for_status = MagicMock()
    return resp


class TestGeocode:
    def test_geocode_success(self, client):
        with patch.object(client._session, "get", return_value=_ok_response()) as mock_get:
            result = client.geocode("123 Main St")
            assert result["place_id"] == "ChIJ_test"
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["address"] == "123 Main St"
            assert call_kwargs[1]["params"]["key"] == "test-key"

    def test_geocode_zero_results(self, client):
        with patch.object(client._session, "get", return_value=_error_response("ZERO_RESULTS")):
            with pytest.raises(GeocodingError, match="ZERO_RESULTS"):
                client.geocode("nonexistent place")

    def test_geocode_request_denied(self, client):
        with patch.object(client._session, "get", return_value=_error_response("REQUEST_DENIED")):
            with pytest.raises(GeocodingError, match="REQUEST_DENIED"):
                client.geocode("123 Main St")

    def test_geocode_invalid_request(self, client):
        with patch.object(client._session, "get", return_value=_error_response("INVALID_REQUEST")):
            with pytest.raises(GeocodingError, match="INVALID_REQUEST"):
                client.geocode("")


class TestReverseGeocode:
    def test_reverse_geocode_success(self, client):
        with patch.object(client._session, "get", return_value=_ok_response()) as mock_get:
            result = client.reverse_geocode(34.0, -118.0)
            assert result["place_id"] == "ChIJ_test"
            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["latlng"] == "34.0,-118.0"
            assert call_kwargs[1]["params"]["key"] == "test-key"

    def test_reverse_geocode_zero_results(self, client):
        with patch.object(client._session, "get", return_value=_error_response("ZERO_RESULTS")):
            with pytest.raises(GeocodingError, match="ZERO_RESULTS"):
                client.reverse_geocode(0.0, 0.0)


class TestRetryLogic:
    @patch("geocoding.client.time.sleep")
    def test_retries_on_over_query_limit_then_succeeds(self, mock_sleep, client):
        responses = [
            _error_response("OVER_QUERY_LIMIT"),
            _error_response("OVER_QUERY_LIMIT"),
            _ok_response(),
        ]
        with patch.object(client._session, "get", side_effect=responses):
            result = client.geocode("123 Main St")
            assert result["place_id"] == "ChIJ_test"
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)

    @patch("geocoding.client.time.sleep")
    def test_raises_rate_limit_after_max_retries(self, mock_sleep, client):
        responses = [_error_response("OVER_QUERY_LIMIT")] * 4
        with patch.object(client._session, "get", side_effect=responses):
            with pytest.raises(RateLimitError):
                client.geocode("123 Main St")
            assert mock_sleep.call_count == 3
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)
            mock_sleep.assert_any_call(4)


class TestNetworkErrors:
    def test_connection_error_raises_upstream(self, client):
        with patch.object(client._session, "get", side_effect=requests.ConnectionError("fail")):
            with pytest.raises(UpstreamError, match="unreachable"):
                client.geocode("123 Main St")

    def test_timeout_raises_upstream(self, client):
        with patch.object(client._session, "get", side_effect=requests.Timeout("timeout")):
            with pytest.raises(UpstreamError, match="unreachable"):
                client.geocode("123 Main St")

    def test_generic_request_exception_raises_upstream(self, client):
        with patch.object(client._session, "get", side_effect=requests.RequestException("err")):
            with pytest.raises(UpstreamError, match="request failed"):
                client.geocode("123 Main St")


class TestClientConfiguration:
    def test_default_timeout(self):
        c = GoogleMapsClient(api_key="key")
        assert c._timeout == 5

    def test_custom_timeout(self):
        c = GoogleMapsClient(api_key="key", timeout=10)
        assert c._timeout == 10

    def test_session_is_created(self):
        c = GoogleMapsClient(api_key="key")
        assert c._session is not None

    def test_timeout_passed_to_request(self, client):
        with patch.object(client._session, "get", return_value=_ok_response()) as mock_get:
            client.geocode("test")
            assert mock_get.call_args[1]["timeout"] == 5
