class GeocodingError(Exception):
    pass


class UpstreamError(GeocodingError):
    pass


class RateLimitError(GeocodingError):
    pass


class InvalidInputError(GeocodingError):
    pass


class InvalidCoordinatesError(GeocodingError):
    pass
