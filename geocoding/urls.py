from django.urls import path

from geocoding.views import DistanceView, GeocodeView, ReverseGeocodeView

urlpatterns = [
    path("geocode/", GeocodeView.as_view(), name="geocode"),
    path("reverse-geocode/", ReverseGeocodeView.as_view(), name="reverse-geocode"),
    path("distance/", DistanceView.as_view(), name="distance"),
]
