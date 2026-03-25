import math
from decimal import Decimal

import pytest

from geocoding.services import DistanceCalculator, DistanceResult, _normalize_query


class TestNormalizeQuery:

    def test_lowercase_conversion(self):
        assert _normalize_query("Beverly Centre") == "beverly centre"

    def test_strip_leading_trailing_whitespace(self):
        assert _normalize_query("  hello world  ") == "hello world"

    def test_collapse_consecutive_whitespace(self):
        assert _normalize_query("beverly   centre") == "beverly centre"

    def test_combined_normalization(self):
        assert _normalize_query("  BEVERLY   centre  ") == "beverly centre"

    def test_tabs_and_newlines_collapsed(self):
        assert _normalize_query("beverly\t\tcentre\n") == "beverly centre"

    def test_idempotent(self):
        first = _normalize_query("Beverly Centre")
        second = _normalize_query(first)
        assert first == second

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            _normalize_query("")

    def test_whitespace_only_raises_value_error(self):
        with pytest.raises(ValueError):
            _normalize_query("   ")

    def test_single_word(self):
        assert _normalize_query("London") == "london"

    def test_already_normalized(self):
        assert _normalize_query("beverly centre") == "beverly centre"


class TestDistanceCalculator:

    def test_known_distance_la_to_nyc(self):
        result = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        assert isinstance(result, DistanceResult)
        assert 3930 < result.distance_km < 3950
        assert result.distance_miles == pytest.approx(
            result.distance_km * 0.621371, abs=1e-4
        )

    def test_same_point_returns_zero(self):
        result = DistanceCalculator.calculate(51.5074, -0.1278, 51.5074, -0.1278)
        assert result.distance_km == 0.0
        assert result.distance_miles == 0.0

    def test_symmetry(self):
        ab = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        ba = DistanceCalculator.calculate(40.7128, -74.0060, 34.0764, -118.3760)
        assert ab.distance_km == ba.distance_km
        assert ab.distance_miles == ba.distance_miles

    def test_non_negative(self):
        result = DistanceCalculator.calculate(-33.8688, 151.2093, 48.8566, 2.3522)
        assert result.distance_km >= 0
        assert result.distance_miles >= 0

    def test_upper_bound(self):
        result = DistanceCalculator.calculate(0, 0, 0, 180)
        assert result.distance_km <= 20015.087

    def test_unit_conversion(self):
        result = DistanceCalculator.calculate(48.8566, 2.3522, 35.6762, 139.6503)
        assert result.distance_miles == pytest.approx(
            result.distance_km * 0.621371, abs=1e-4
        )

    def test_result_rounded_to_4_decimal_places(self):
        result = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        km_str = str(result.distance_km)
        miles_str = str(result.distance_miles)
        if "." in km_str:
            assert len(km_str.split(".")[1]) <= 4
        if "." in miles_str:
            assert len(miles_str.split(".")[1]) <= 4

    def test_result_stores_decimal_coordinates(self):
        result = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        assert isinstance(result.origin_lat, Decimal)
        assert isinstance(result.origin_lng, Decimal)
        assert isinstance(result.destination_lat, Decimal)
        assert isinstance(result.destination_lng, Decimal)

    def test_latitude_out_of_range_raises(self):
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(91, 0, 0, 0)
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(0, 0, -91, 0)

    def test_longitude_out_of_range_raises(self):
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(0, 181, 0, 0)
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(0, 0, 0, -181)

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(float("nan"), 0, 0, 0)

    def test_inf_raises(self):
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(0, float("inf"), 0, 0)

    def test_boundary_coordinates(self):
        """Boundary values (-90, 90, -180, 180) are accepted."""
        result = DistanceCalculator.calculate(-90, -180, 90, 180)
        assert result.distance_km >= 0
        assert result.distance_km <= 20015.087
