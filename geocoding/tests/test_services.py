from decimal import Decimal

import pytest

from geocoding.services import DistanceCalculator, DistanceResult, _normalize_query


class TestNormalizeQuery:

    def test_combined_normalization(self):
        assert _normalize_query("  BEVERLY   centre  ") == "beverly centre"

    def test_tabs_and_newlines(self):
        assert _normalize_query("beverly\t\tcentre\n") == "beverly centre"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _normalize_query("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            _normalize_query("   ")


class TestDistanceCalculator:

    def test_known_distance_la_to_nyc(self):
        result = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        assert isinstance(result, DistanceResult)
        assert 3930 < result.distance_km < 3950
        assert result.distance_miles == pytest.approx(result.distance_km * 0.621371, abs=1e-4)

    def test_same_point_returns_zero(self):
        result = DistanceCalculator.calculate(51.5074, -0.1278, 51.5074, -0.1278)
        assert result.distance_km == 0.0

    def test_symmetry(self):
        ab = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        ba = DistanceCalculator.calculate(40.7128, -74.0060, 34.0764, -118.3760)
        assert ab.distance_km == ba.distance_km

    def test_coordinates_stored_as_decimal(self):
        result = DistanceCalculator.calculate(34.0764, -118.3760, 40.7128, -74.0060)
        assert isinstance(result.origin_lat, Decimal)

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(91, 0, 0, 0)

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            DistanceCalculator.calculate(float("nan"), 0, 0, 0)
