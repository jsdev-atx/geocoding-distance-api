import time

import requests

from geocoding.exceptions import GeocodingError, RateLimitError, UpstreamError


class GoogleMapsClient:
    """HTTP client for Google Maps Geocoding API with retry logic."""

    BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    DEFAULT_TIMEOUT = 5  # seconds
    MAX_RETRIES = 3
    BACKOFF_DELAYS = (1, 2, 4)  # seconds

    def __init__(self, api_key: str, timeout: int = DEFAULT_TIMEOUT):
        self._api_key = api_key
        self._timeout = timeout
        self._session = requests.Session()

    def geocode(self, address: str) -> dict:
        params = {"address": address, "key": self._api_key}
        return self._request(params)

    def reverse_geocode(self, lat: float, lng: float) -> dict:
        params = {"latlng": f"{lat},{lng}", "key": self._api_key}
        return self._request(params)

    def _request(self, params: dict) -> dict:
        """Send request with exponential backoff on OVER_QUERY_LIMIT."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self._session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                data = response.json()
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise UpstreamError(
                    f"Google Maps API unreachable: {exc}"
                ) from exc
            except requests.RequestException as exc:
                raise UpstreamError(
                    f"Google Maps API request failed: {exc}"
                ) from exc

            status = data.get("status", "UNKNOWN_ERROR")

            if status == "OK":
                return data["results"][0]

            if status == "OVER_QUERY_LIMIT":
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.BACKOFF_DELAYS[attempt])
                    continue
                raise RateLimitError(
                    "Google Maps API rate limit exceeded after retries."
                )

            if status == "ZERO_RESULTS":
                raise GeocodingError("ZERO_RESULTS")

            # REQUEST_DENIED, INVALID_REQUEST, UNKNOWN_ERROR, etc.
            raise GeocodingError(status)
