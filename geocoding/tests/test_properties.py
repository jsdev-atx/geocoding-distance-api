from hypothesis import given
from hypothesis import strategies as st

from geocoding.services import DistanceCalculator, _normalize_query

latitudes = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
longitudes = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
non_whitespace_text = st.text(min_size=1).filter(lambda s: s.strip())


class TestNormalizationProperties:

    @given(query=non_whitespace_text)
    def test_output_is_lowercase_and_stripped(self, query):
        result = _normalize_query(query)
        assert result == result.lower()
        assert result == result.strip()
        assert "  " not in result

    @given(query=non_whitespace_text)
    def test_idempotent(self, query):
        once = _normalize_query(query)
        twice = _normalize_query(once)
        assert once == twice


class TestHaversineProperties:

    @given(lat=latitudes, lng=longitudes)
    def test_distance_to_self_is_zero(self, lat, lng):
        result = DistanceCalculator.calculate(lat, lng, lat, lng)
        assert result.distance_km == 0.0

    @given(lat1=latitudes, lng1=longitudes, lat2=latitudes, lng2=longitudes)
    def test_symmetric(self, lat1, lng1, lat2, lng2):
        ab = DistanceCalculator.calculate(lat1, lng1, lat2, lng2)
        ba = DistanceCalculator.calculate(lat2, lng2, lat1, lng1)
        assert ab.distance_km == ba.distance_km

    @given(
        origin_lat=latitudes, origin_lng=longitudes,
        dest_lat=latitudes, dest_lng=longitudes,
    )
    def test_non_negative_and_bounded(self, origin_lat, origin_lng, dest_lat, dest_lng):
        result = DistanceCalculator.calculate(origin_lat, origin_lng, dest_lat, dest_lng)
        assert 0 <= result.distance_km <= 20015.087

    @given(
        origin_lat=latitudes, origin_lng=longitudes,
        dest_lat=latitudes, dest_lng=longitudes,
    )
    def test_unit_conversion(self, origin_lat, origin_lng, dest_lat, dest_lng):
        result = DistanceCalculator.calculate(origin_lat, origin_lng, dest_lat, dest_lng)
        assert abs(result.distance_miles - result.distance_km * 0.621371) <= 1e-4
