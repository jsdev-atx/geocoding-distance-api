from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class GeocodeLookup(models.Model):

    LOOKUP_TYPE_CHOICES = [
        ("forward", "Forward"),
        ("reverse", "Reverse"),
    ]

    normalized_query = models.CharField(
        max_length=512,
        db_index=True,
    )
    formatted_address = models.CharField(
        max_length=1024,
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        db_index=True,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90),
        ],
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        db_index=True,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180),
        ],
    )
    place_id = models.CharField(
        max_length=255,
        unique=True,
    )
    address_components = models.JSONField(
        default=dict,
    )
    lookup_type = models.CharField(
        max_length=10,
        choices=LOOKUP_TYPE_CHOICES,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "geocode_lookups"
        indexes = [
            models.Index(
                fields=["normalized_query", "lookup_type"],
                name="idx_query_type",
            ),
            models.Index(
                fields=["latitude", "longitude"],
                name="idx_lat_lng",
            ),
        ]
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if not self.normalized_query or not self.normalized_query.strip():
            raise ValidationError(
                {"normalized_query": "Normalized query must not be empty."}
            )
        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            raise ValidationError(
                {"latitude": "Latitude must be between -90 and 90."}
            )
        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            raise ValidationError(
                {"longitude": "Longitude must be between -180 and 180."}
            )

    def __str__(self):
        return f"{self.normalized_query} → {self.formatted_address}"


class DistanceCalculation(models.Model):

    origin_lat = models.DecimalField(max_digits=10, decimal_places=7)
    origin_lng = models.DecimalField(max_digits=10, decimal_places=7)
    destination_lat = models.DecimalField(max_digits=10, decimal_places=7)
    destination_lng = models.DecimalField(max_digits=10, decimal_places=7)
    distance_km = models.FloatField()
    distance_miles = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "distance_calculations"
        indexes = [
            models.Index(
                fields=["origin_lat", "origin_lng"],
                name="idx_origin_coords",
            ),
            models.Index(
                fields=["destination_lat", "destination_lng"],
                name="idx_dest_coords",
            ),
        ]

    def __str__(self):
        return (
            f"({self.origin_lat},{self.origin_lng}) → "
            f"({self.destination_lat},{self.destination_lng}): "
            f"{self.distance_km:.2f} km"
        )
