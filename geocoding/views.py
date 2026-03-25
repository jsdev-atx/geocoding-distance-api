from decimal import Decimal

from django.conf import settings
from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from geocoding.client import GoogleMapsClient
from geocoding.exceptions import (
    GeocodingError,
    InvalidCoordinatesError,
    InvalidInputError,
    RateLimitError,
    UpstreamError,
)
from geocoding.models import DistanceCalculation
from geocoding.serializers import (
    DistanceResponseSerializer,
    DistanceSerializer,
    ForwardGeocodeSerializer,
    GeocodingResponseSerializer,
    ReverseGeocodeSerializer,
)
from geocoding.services import DistanceCalculator, GeocodingService


def _success_envelope(data: dict) -> dict:
    return {"status": "success", "data": data}


def _error_envelope(code: str, message: str) -> dict:
    return {"status": "error", "error": {"code": code, "message": message}}


def custom_exception_handler(exc, context):
    # Handle domain-specific exceptions first
    if isinstance(exc, InvalidInputError):
        body = _error_envelope("INVALID_INPUT", str(exc))
        return Response(body, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, InvalidCoordinatesError):
        body = _error_envelope("INVALID_COORDINATES", str(exc))
        return Response(body, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, GeocodingError) and str(exc) == "ZERO_RESULTS":
        body = _error_envelope(
            "GEOCODE_NOT_FOUND",
            "No results found for the provided input.",
        )
        return Response(body, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, RateLimitError):
        body = _error_envelope(
            "RATE_LIMIT_EXCEEDED",
            "Upstream service rate limit exceeded. Please retry later.",
        )
        response = Response(body, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        response["Retry-After"] = "60"
        return response

    if isinstance(exc, UpstreamError):
        body = _error_envelope(
            "UPSTREAM_ERROR",
            "The upstream geocoding service is unavailable.",
        )
        return Response(body, status=status.HTTP_502_BAD_GATEWAY)

    if isinstance(exc, GeocodingError):
        body = _error_envelope("GEOCODING_ERROR", str(exc))
        return Response(body, status=status.HTTP_502_BAD_GATEWAY)

    if isinstance(exc, DatabaseError):
        body = _error_envelope("INTERNAL_ERROR", "A database error occurred.")
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Fall back to DRF's default handler for framework exceptions
    response = exception_handler(exc, context)
    if response is not None:
        # Re-format DRF validation errors into our envelope
        if isinstance(response.data, dict):
            # Determine error code from field names
            coord_fields = {"lat", "lng", "origin_lat", "origin_lng", "dest_lat", "dest_lng"}
            error_fields = set(response.data.keys())
            if error_fields & coord_fields:
                code = "INVALID_COORDINATES"
            else:
                code = "INVALID_INPUT"

            # Build a human-readable message from the validation errors
            messages = []
            for field, errors in response.data.items():
                if isinstance(errors, list):
                    for err in errors:
                        messages.append(f"{field}: {err}")
                else:
                    messages.append(f"{field}: {errors}")
            message = "; ".join(messages) if messages else "Validation error."
        elif isinstance(response.data, list):
            code = "INVALID_INPUT"
            message = "; ".join(str(e) for e in response.data)
        else:
            code = "INVALID_INPUT"
            message = str(response.data)

        response.data = _error_envelope(code, message)

    return response


def _get_geocoding_service() -> GeocodingService:
    client = GoogleMapsClient(api_key=settings.GOOGLE_MAPS_API_KEY)
    return GeocodingService(google_client=client)


class GeocodeView(APIView):

    def get(self, request):
        serializer = ForwardGeocodeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        address = serializer.validated_data["address"]
        service = _get_geocoding_service()
        result = service.geocode(address)

        response_serializer = GeocodingResponseSerializer(
            {
                "formatted_address": result.formatted_address,
                "latitude": result.latitude,
                "longitude": result.longitude,
                "place_id": result.place_id,
                "address_components": result.address_components,
            }
        )
        return Response(
            _success_envelope(response_serializer.data),
            status=status.HTTP_200_OK,
        )


class ReverseGeocodeView(APIView):

    def get(self, request):
        serializer = ReverseGeocodeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data["lat"]
        lng = serializer.validated_data["lng"]
        service = _get_geocoding_service()
        result = service.reverse_geocode(Decimal(str(lat)), Decimal(str(lng)))

        response_serializer = GeocodingResponseSerializer(
            {
                "formatted_address": result.formatted_address,
                "latitude": result.latitude,
                "longitude": result.longitude,
                "place_id": result.place_id,
                "address_components": result.address_components,
            }
        )
        return Response(
            _success_envelope(response_serializer.data),
            status=status.HTTP_200_OK,
        )


class DistanceView(APIView):

    def get(self, request):
        serializer = DistanceSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        origin_lat = float(serializer.validated_data["origin_lat"])
        origin_lng = float(serializer.validated_data["origin_lng"])
        dest_lat = float(serializer.validated_data["dest_lat"])
        dest_lng = float(serializer.validated_data["dest_lng"])

        result = DistanceCalculator.calculate(
            origin_lat, origin_lng, dest_lat, dest_lng
        )

        # Persist the calculation for analytics/auditing
        DistanceCalculation.objects.create(
            origin_lat=result.origin_lat,
            origin_lng=result.origin_lng,
            destination_lat=result.destination_lat,
            destination_lng=result.destination_lng,
            distance_km=result.distance_km,
            distance_miles=result.distance_miles,
        )

        response_serializer = DistanceResponseSerializer(
            {
                "origin": {
                    "latitude": result.origin_lat,
                    "longitude": result.origin_lng,
                },
                "destination": {
                    "latitude": result.destination_lat,
                    "longitude": result.destination_lng,
                },
                "distance": {
                    "kilometers": result.distance_km,
                    "miles": result.distance_miles,
                },
            }
        )
        return Response(
            _success_envelope(response_serializer.data),
            status=status.HTTP_200_OK,
        )
