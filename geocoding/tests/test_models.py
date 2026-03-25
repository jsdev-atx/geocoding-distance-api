import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from geocoding.models import GeocodeLookup, DistanceCalculation


@pytest.mark.django_db
class TestGeocodeLookupModel:

    def _create_lookup(self, **overrides):
        defaults = {
            "normalized_query": "beverly centre",
            "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
            "latitude": Decimal("34.0764200"),
            "longitude": Decimal("-118.3760200"),
            "place_id": "ChIJMyzlkPa4woARkNMBOsEcCBQ",
            "address_components": {"locality": "Los Angeles"},
            "lookup_type": "forward",
        }
        defaults.update(overrides)
        return GeocodeLookup(**defaults)

    def test_create_valid_forward_lookup(self):
        lookup = self._create_lookup()
        lookup.full_clean()
        lookup.save()
        assert lookup.pk is not None
        assert lookup.lookup_type == "forward"

    def test_create_valid_reverse_lookup(self):
        lookup = self._create_lookup(
            lookup_type="reverse",
            normalized_query="34.0764200,-118.3760200",
        )
        lookup.full_clean()
        lookup.save()
        assert lookup.lookup_type == "reverse"

    def test_place_id_uniqueness(self):
        self._create_lookup().save()
        dup = self._create_lookup(normalized_query="other query")
        with pytest.raises(IntegrityError):
            dup.save()

    def test_lookup_type_choices(self):
        lookup = self._create_lookup(lookup_type="invalid")
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_latitude_out_of_range_high(self):
        lookup = self._create_lookup(latitude=Decimal("91.0"))
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_latitude_out_of_range_low(self):
        lookup = self._create_lookup(latitude=Decimal("-91.0"))
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_longitude_out_of_range_high(self):
        lookup = self._create_lookup(longitude=Decimal("181.0"))
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_longitude_out_of_range_low(self):
        lookup = self._create_lookup(longitude=Decimal("-181.0"))
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_normalized_query_empty_rejected(self):
        lookup = self._create_lookup(normalized_query="")
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_normalized_query_whitespace_only_rejected(self):
        lookup = self._create_lookup(normalized_query="   ")
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_boundary_latitude_values(self):
        """Boundary values for latitude should be accepted."""
        for lat in [Decimal("-90"), Decimal("90")]:
            lookup = self._create_lookup(
                latitude=lat,
                place_id=f"place_{lat}",
            )
            lookup.full_clean()

    def test_boundary_longitude_values(self):
        """Boundary values for longitude should be accepted."""
        for lng in [Decimal("-180"), Decimal("180")]:
            lookup = self._create_lookup(
                longitude=lng,
                place_id=f"place_{lng}",
            )
            lookup.full_clean()

    def test_str_representation(self):
        lookup = self._create_lookup()
        expected = "beverly centre → Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA"
        assert str(lookup) == expected

    def test_ordering_by_created_at_desc(self):
        """Meta ordering is -created_at."""
        assert GeocodeLookup._meta.ordering == ["-created_at"]

    def test_db_table_name(self):
        assert GeocodeLookup._meta.db_table == "geocode_lookups"


@pytest.mark.django_db
class TestDistanceCalculationModel:

    def _create_calculation(self, **overrides):
        defaults = {
            "origin_lat": Decimal("34.0764200"),
            "origin_lng": Decimal("-118.3760200"),
            "destination_lat": Decimal("40.7128000"),
            "destination_lng": Decimal("-74.0060000"),
            "distance_km": 3940.0691,
            "distance_miles": 2448.3776,
        }
        defaults.update(overrides)
        return DistanceCalculation(**defaults)

    def test_create_valid_calculation(self):
        calc = self._create_calculation()
        calc.save()
        assert calc.pk is not None
        assert calc.distance_km == 3940.0691
        assert calc.distance_miles == 2448.3776

    def test_created_at_auto_set(self):
        calc = self._create_calculation()
        calc.save()
        assert calc.created_at is not None

    def test_str_representation(self):
        calc = self._create_calculation()
        result = str(calc)
        assert "34.0764200" in result
        assert "-118.3760200" in result
        assert "40.7128000" in result
        assert "3940.07 km" in result

    def test_db_table_name(self):
        assert DistanceCalculation._meta.db_table == "distance_calculations"

    def test_composite_indexes_exist(self):
        index_names = [idx.name for idx in DistanceCalculation._meta.indexes]
        assert "idx_origin_coords" in index_names
        assert "idx_dest_coords" in index_names

    def test_origin_index_fields(self):
        origin_idx = next(
            idx for idx in DistanceCalculation._meta.indexes if idx.name == "idx_origin_coords"
        )
        assert origin_idx.fields == ["origin_lat", "origin_lng"]

    def test_dest_index_fields(self):
        dest_idx = next(
            idx for idx in DistanceCalculation._meta.indexes if idx.name == "idx_dest_coords"
        )
        assert dest_idx.fields == ["destination_lat", "destination_lng"]
