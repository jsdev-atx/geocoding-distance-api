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

    def test_create_and_save(self):
        lookup = self._create_lookup()
        lookup.full_clean()
        lookup.save()
        assert lookup.pk is not None

    def test_place_id_uniqueness(self):
        self._create_lookup().save()
        dup = self._create_lookup(normalized_query="other query")
        with pytest.raises(IntegrityError):
            dup.save()

    def test_invalid_lookup_type_rejected(self):
        lookup = self._create_lookup(lookup_type="invalid")
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_out_of_range_coordinates_rejected(self):
        for field, val in [("latitude", "91"), ("latitude", "-91"), ("longitude", "181"), ("longitude", "-181")]:
            lookup = self._create_lookup(**{field: Decimal(val)})
            with pytest.raises(ValidationError):
                lookup.full_clean()

    def test_empty_query_rejected(self):
        lookup = self._create_lookup(normalized_query="")
        with pytest.raises(ValidationError):
            lookup.full_clean()

    def test_str(self):
        lookup = self._create_lookup()
        assert "beverly centre" in str(lookup)
        assert "Beverly Center" in str(lookup)


@pytest.mark.django_db
class TestDistanceCalculationModel:

    def test_create_and_persist(self):
        calc = DistanceCalculation(
            origin_lat=Decimal("34.0764200"),
            origin_lng=Decimal("-118.3760200"),
            destination_lat=Decimal("40.7128000"),
            destination_lng=Decimal("-74.0060000"),
            distance_km=3940.0691,
            distance_miles=2448.3776,
        )
        calc.save()
        assert calc.pk is not None
        assert calc.created_at is not None

    def test_indexes_exist(self):
        index_names = [idx.name for idx in DistanceCalculation._meta.indexes]
        assert "idx_origin_coords" in index_names
        assert "idx_dest_coords" in index_names
