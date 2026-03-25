# Geocoding & Distance API

A Django REST API that wraps the Google Maps Geocoding API and adds Haversine distance calculation between coordinates. Built with Django 4.2+, Django REST Framework, and PostgreSQL (SQLite for local dev).

## What it does

Three endpoints, all under `/api/v1/`:

- `GET /api/v1/geocode/?address=...` — forward geocode (address → coordinates)
- `GET /api/v1/reverse-geocode/?lat=...&lng=...` — reverse geocode (coordinates → address)
- `GET /api/v1/distance/?origin_lat=...&origin_lng=...&dest_lat=...&dest_lng=...` — Haversine distance between two points

Every response uses a consistent envelope:

```json
{ "status": "success", "data": { ... } }
{ "status": "error", "error": { "code": "...", "message": "..." } }
```

## Key design choices

**DB-backed lookup deduplication** — Before hitting Google, the service checks if we've already geocoded that query. Addresses are normalized (lowercased, whitespace-collapsed) so "Beverly Centre", " BEVERLY centre ", and "beverly centre" all resolve to the same cached result. This cuts down on API calls and speeds up repeated lookups.

**Haversine formula** — Distance is calculated server-side using the standard great-circle formula. No external API needed. Results come back in both km and miles, rounded to 4 decimal places. The calculation is also persisted for analytics.

**Service layer pattern** — Views are thin controllers. `GeocodingService` handles the cache-or-fetch logic, `DistanceCalculator` is a pure static method, and `GoogleMapsClient` handles HTTP with exponential backoff on rate limits (1s, 2s, 4s delays, 3 retries max).

**Custom exception hierarchy** — Domain exceptions (`UpstreamError`, `RateLimitError`, `InvalidInputError`, etc.) get mapped to appropriate HTTP status codes by a custom DRF exception handler. Rate limit responses include a `Retry-After` header.

**Environment-based config** — Uses `python-decouple` to read `SECRET_KEY`, `GOOGLE_MAPS_API_KEY`, `DATABASE_URL`, etc. from environment variables. Supports SQLite, PostgreSQL, and MySQL via `DATABASE_URL` format.

## Project structure

```
geocoding/
├── client.py          # Google Maps HTTP client with retry logic
├── exceptions.py      # Domain exception hierarchy
├── models.py          # GeocodeLookup + DistanceCalculation models
├── serializers.py     # DRF request/response serializers
├── services.py        # GeocodingService, DistanceCalculator, query normalization
├── views.py           # API views + custom exception handler
├── urls.py            # Route definitions
└── tests/             # Unit, integration, and property-based tests
```

## Running locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# Copy .env.example to .env and fill in your Google Maps API key
cp .env.example .env

python manage.py migrate
python manage.py runserver
```

## Running with Docker

```bash
# Set env vars in a .env file or export them
docker-compose up --build
```

This starts PostgreSQL, the Django app behind Gunicorn, and Nginx as a reverse proxy on port 80 (HTTP→HTTPS redirect on 443).

## Tests

```bash
pytest
```

45 tests covering unit tests, integration tests (all three endpoints with mocked Google responses), and property-based tests using Hypothesis for normalization invariants and Haversine mathematical properties.

## Tech stack

- Django 4.2 + Django REST Framework
- Google Maps Geocoding API
- PostgreSQL (production) / SQLite (local dev)
- Gunicorn + Nginx (Docker deployment)
- Hypothesis (property-based testing)
- pytest + pytest-django
