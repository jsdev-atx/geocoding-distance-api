from decimal import Decimal

from geocoding.serializers import (
    DistanceResponseSerializer,
    DistanceSerializer,
    ForwardGeocodeSerializer,
    GeocodingResponseSerializer,
    ReverseGeocodeSerializer,
)


class TestForwardGeocodeSerializer:
    def test_valid_address(self):
        s = ForwardGeocodeSerializer(data={"address": "123 Main St"})
        assert s.is_valid(), s.errors

    def test_empty_address_rejected(self):
        s = ForwardGeocodeSerializer(data={"address": ""})
        assert not s.is_valid()
        assert "address" in s.errors

    def test_missing_address_rejected(self):
        s = ForwardGeocodeSerializer(data={})
        assert not s.is_valid()
        assert "address" in s.errors

    def test_whitespace_only_address_rejected(self):
        s = ForwardGeocodeSerializer(data={"address": "   "})
        assert not s.is_valid()
        assert "address" in s.errors


class TestReverseGeocodeSerializer:
    def test_valid_coordinates(self):
        s = ReverseGeocodeSerializer(data={"lat": "40.7128", "lng": "-74.006"})
        assert s.is_valid(), s.errors

    def test_lat_out_of_range_high(self):
        s = ReverseGeocodeSerializer(data={"lat": "91", "lng": "0"})
        assert not s.is_valid()
        assert "lat" in s.errors

    def test_lat_out_of_range_low(self):
        s = ReverseGeocodeSerializer(data={"lat": "-91", "lng": "0"})
        assert not s.is_valid()
        assert "lat" in s.errors

    def test_lng_out_of_range_high(self):
        s = ReverseGeocodeSerializer(data={"lat": "0", "lng": "181"})
        assert not s.is_valid()
        assert "lng" in s.errors

    def test_lng_out_of_range_low(self):
        s = ReverseGeocodeSerializer(data={"lat": "0", "lng": "-181"})
        assert not s.is_valid()
        assert "lng" in s.errors

    def test_boundary_values_accepted(self):
        s = ReverseGeocodeSerializer(data={"lat": "90", "lng": "180"})
        assert s.is_valid(), s.errors

        s = ReverseGeocodeSerializer(data={"lat": "-90", "lng": "-180"})
        assert s.is_valid(), s.errors

    def test_missing_lat_rejected(self):
        s = ReverseGeocodeSerializer(data={"lng": "0"})
        assert not s.is_valid()
        assert "lat" in s.errors

    def test_missing_lng_rejected(self):
        s = ReverseGeocodeSerializer(data={"lat": "0"})
        assert not s.is_valid()
        assert "lng" in s.errors


class TestDistanceSerializer:
    def test_valid_coordinates(self):
        data = {
            "origin_lat": "34.0764",
            "origin_lng": "-118.376",
            "dest_lat": "40.7128",
            "dest_lng": "-74.006",
        }
        s = DistanceSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_origin_lat_out_of_range(self):
        data = {
            "origin_lat": "91",
            "origin_lng": "0",
            "dest_lat": "0",
            "dest_lng": "0",
        }
        s = DistanceSerializer(data=data)
        assert not s.is_valid()
        assert "origin_lat" in s.errors

    def test_dest_lng_out_of_range(self):
        data = {
            "origin_lat": "0",
            "origin_lng": "0",
            "dest_lat": "0",
            "dest_lng": "181",
        }
        s = DistanceSerializer(data=data)
        assert not s.is_valid()
        assert "dest_lng" in s.errors

    def test_missing_field_rejected(self):
        data = {
            "origin_lat": "0",
            "origin_lng": "0",
            "dest_lat": "0",
        }
        s = DistanceSerializer(data=data)
        assert not s.is_valid()
        assert "dest_lng" in s.errors

    def test_boundary_values_accepted(self):
        data = {
            "origin_lat": "-90",
            "origin_lng": "-180",
            "dest_lat": "90",
            "dest_lng": "180",
        }
        s = DistanceSerializer(data=data)
        assert s.is_valid(), s.errors


class TestGeocodingResponseSerializer:
    def test_valid_response_data(self):
        data = {
            "formatted_address": "123 Main St, City, ST 12345",
            "latitude": Decimal("34.0764200"),
            "longitude": Decimal("-118.3760200"),
            "place_id": "ChIJMyzlkPa4woARkNMBOsEcCBQ",
            "address_components": {"locality": "Los Angeles"},
        }
        s = GeocodingResponseSerializer(data)
        assert s.data["formatted_address"] == data["formatted_address"]
        assert s.data["place_id"] == data["place_id"]


class TestDistanceResponseSerializer:
    def test_valid_response_data(self):
        data = {
            "origin": {
                "latitude": Decimal("34.0764000"),
                "longitude": Decimal("-118.3760000"),
            },
            "destination": {
                "latitude": Decimal("40.7128000"),
                "longitude": Decimal("-74.0060000"),
            },
            "distance": {
                "kilometers": 3940.0691,
                "miles": 2448.3776,
            },
        }
        s = DistanceResponseSerializer(data)
        assert s.data["distance"]["kilometers"] == 3940.0691
        assert s.data["distance"]["miles"] == 2448.3776
