from hypothesis import given
from hypothesis import strategies as st

from geocoding.services import DistanceCalculator

latitudes = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
longitudes = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)


class TestUnitConversionConsistency:

    @given(
        origin_lat=latitudes,
        origin_lng=longitudes,
        dest_lat=latitudes,
        dest_lng=longitudes,
    )
    def test_miles_equals_km_times_conversion_factor(
        self, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        result = DistanceCalculator.calculate(origin_lat, origin_lng, dest_lat, dest_lng)
        expected_miles = result.distance_km * 0.621371
        assert abs(result.distance_miles - expected_miles) <= 1e-4


class TestHaversineNonNegativity:

    @given(
        origin_lat=latitudes,
        origin_lng=longitudes,
        dest_lat=latitudes,
        dest_lng=longitudes,
    )
    def test_distance_is_non_negative(
        self, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        result = DistanceCalculator.calculate(origin_lat, origin_lng, dest_lat, dest_lng)
        assert result.distance_km >= 0
        assert result.distance_miles >= 0


class TestHaversineIdentity:

    @given(lat=latitudes, lng=longitudes)
    def test_distance_to_self_is_zero(self, lat, lng):
        result = DistanceCalculator.calculate(lat, lng, lat, lng)
        assert result.distance_km == 0.0
        assert result.distance_miles == 0.0


class TestHaversineSymmetry:

    @given(
        lat1=latitudes,
        lng1=longitudes,
        lat2=latitudes,
        lng2=longitudes,
    )
    def test_distance_is_symmetric(self, lat1, lng1, lat2, lng2):
        ab = DistanceCalculator.calculate(lat1, lng1, lat2, lng2)
        ba = DistanceCalculator.calculate(lat2, lng2, lat1, lng1)
        assert ab.distance_km == ba.distance_km
        assert ab.distance_miles == ba.distance_miles


class TestHaversineTriangleInequality:

    @given(
        lat_a=latitudes,
        lng_a=longitudes,
        lat_b=latitudes,
        lng_b=longitudes,
        lat_c=latitudes,
        lng_c=longitudes,
    )
    def test_triangle_inequality_holds(
        self, lat_a, lng_a, lat_b, lng_b, lat_c, lng_c
    ):
        ac = DistanceCalculator.calculate(lat_a, lng_a, lat_c, lng_c)
        ab = DistanceCalculator.calculate(lat_a, lng_a, lat_b, lng_b)
        bc = DistanceCalculator.calculate(lat_b, lng_b, lat_c, lng_c)
        assert ac.distance_km <= ab.distance_km + bc.distance_km + 1e-3


class TestHaversineUpperBound:

    @given(
        origin_lat=latitudes,
        origin_lng=longitudes,
        dest_lat=latitudes,
        dest_lng=longitudes,
    )
    def test_distance_within_upper_bound(
        self, origin_lat, origin_lng, dest_lat, dest_lng
    ):
        result = DistanceCalculator.calculate(origin_lat, origin_lng, dest_lat, dest_lng)
        assert result.distance_km <= 20015.087
