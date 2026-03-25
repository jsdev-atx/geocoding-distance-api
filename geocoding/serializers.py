from rest_framework import serializers


class ForwardGeocodeSerializer(serializers.Serializer):
    address = serializers.CharField(required=True, allow_blank=False)


class ReverseGeocodeSerializer(serializers.Serializer):

    lat = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-90,
        max_value=90,
    )
    lng = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-180,
        max_value=180,
    )


class DistanceSerializer(serializers.Serializer):

    origin_lat = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-90,
        max_value=90,
    )
    origin_lng = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-180,
        max_value=180,
    )
    dest_lat = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-90,
        max_value=90,
    )
    dest_lng = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-180,
        max_value=180,
    )


class GeocodingResponseSerializer(serializers.Serializer):

    formatted_address = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    place_id = serializers.CharField()
    address_components = serializers.DictField()


class _LatLngSerializer(serializers.Serializer):

    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)


class _DistanceValuesSerializer(serializers.Serializer):

    kilometers = serializers.FloatField()
    miles = serializers.FloatField()


class DistanceResponseSerializer(serializers.Serializer):

    origin = _LatLngSerializer()
    destination = _LatLngSerializer()
    distance = _DistanceValuesSerializer()
