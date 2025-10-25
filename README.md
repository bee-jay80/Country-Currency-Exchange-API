# Country Currency & Exchange API

A Django REST API that fetches country data from an external API, caches it in a database, and exposes CRUD and status endpoints.

## Features

- POST /countries/refresh — fetch countries and exchange rates, compute estimated GDPs, and cache in DB
- GET /countries — list cached countries (filter by region, currency; sort by GDP)
- GET /countries/:name — get a country by name (case-insensitive)
- DELETE /countries/:name — delete a country by name
- GET /status — show total countries and last refresh timestamp
- GET /countries/image — serve generated summary image at `cache/summary.png`

## External APIs

- Countries: `https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies`
- Exchange rates: `https://open.er-api.com/v6/latest/USD`

## Requirements

- Python 3.11+
- MySQL server (optional) or SQLite (default)

Dependencies are listed in `requirements.txt`.

## Configuration (.env)

Create a `.env` file in the project root (same directory as `manage.py`). Example:

DJANGO_SECRET_KEY=your_secret_key
DEBUG=True
# Optional: use MySQL by setting DATABASE_URL; otherwise sqlite will be used
# Example MySQL URL:
# DATABASE_URL=mysql://dbuser:dbpassword@dbhost:3306/dbname

If you don't set `DATABASE_URL`, the project will use the bundled sqlite `db.sqlite3`.

## Setup (local)

1. Create a virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/Scripts/activate    # on Windows PowerShell use .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create `.env` as described above.

3. Run migrations:

```bash
python manage.py migrate
```

4. Run server:

```bash
python manage.py runserver
```

## Endpoints

- POST /countries/refresh
  - Fetch countries + exchange rates, upsert records, and generate `cache/summary.png`.
  - Returns 503 if either external API fails.

- GET /countries
  - Query params: `region`, `currency`, `sort` (e.g., `gdp_desc`, `gdp_asc`, `name_asc`, `name_desc`)

- GET /countries/:name
  - 404 response: `{ "error": "Country not found" }`

- DELETE /countries/:name
  - 204 on success, 404 if not found

- GET /status
  - `{ "total_countries": 250, "last_refreshed_at": "2025-10-22T18:00:00Z" }`

- GET /countries/image
  - Returns `cache/summary.png` image. If not found: `{ "error": "Summary image not found" }`

## Notes & Behavior

- When `/countries/refresh` runs:
  - If a country has multiple currencies, only the first currency code is used.
  - If `currencies` is empty, `currency_code` and `exchange_rate` will be `null` and `estimated_gdp` will be `0`.
  - If a `currency_code` is not present in exchange rates, `exchange_rate` and `estimated_gdp` will be `null`.
  - Matching for upsert is case-insensitive on `name`.
  - `estimated_gdp` is computed as `population * random(1000–2000) / exchange_rate` when `exchange_rate` is available.
  - A summary image is generated and saved to `cache/summary.png`.

## Troubleshooting

- If you see `Could not fetch data from Countries API` or similar, the external APIs might be down or blocked.
- To force a fresh cached image or data, run the refresh endpoint.

## Next steps / Improvements

- Add authenticated admin endpoints to schedule refreshes
- Add unit tests for the refresh logic and utilities
- Add CI checks and linting

---

If you'd like, I can:
- Switch the default DB to MySQL in the `.env` example and demonstrate a local docker-compose MySQL setup.
- Add unit tests for the refresh flow and image generation.
