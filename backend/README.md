# Campus Lost and Found Backend

Python 3.11+ and FastAPI backend for GhostComm Find, a campus lost-and-found platform. No frontend is included.

## Features

- Register, log in with email/password, and retrieve the current user.
- Argon2 password hashing, expiring JWT access tokens, ownership checks, and request limits.
- Create, browse, search, update, resolve, reopen, and delete lost/found reports.
- Upload up to five images/videos per report. Downloads require authentication.
- Match opposite report types with Gemini using descriptions and images; save ranked suggestions.
- Search found/lost reports with a natural-language description using Gemini.
- Private conversations between a report owner and a person contacting them.
- SQLite for development, PostgreSQL support, Alembic migrations, and interactive API documentation.

## Local setup

Run all commands from this directory:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Set `JWT_SECRET` in `.env` to the generated value. The server rejects the example placeholder. Set `GEMINI_API_KEY` to the recipient's Gemini key when available. Set `GEMINI_MODEL` to a model supported by their account; the default is `gemini-flash-latest`. The rest of the API works without a Gemini key; AI endpoints return HTTP 503 until configured.

```sh
mkdir -p data
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

Open [Swagger documentation](http://localhost:8000/docs). Register first, then use **Authorize**, entering the email in the username field and the account password. The login endpoint uses OAuth2 form fields, not JSON. Every endpoint except registration, login, health, and API documentation requires a bearer token.

The access token expires after 30 minutes by default. Log in again when it expires. No refresh-token or logout/revocation endpoint is included.

For an expendable development database, `python -m app.init_db` can also create tables. Prefer Alembic for persistent databases; do not mix the two initialization methods on one database. `create_all` does not migrate existing tables.

## Configuration

| Variable | Purpose |
| --- | --- |
| `JWT_SECRET` | Required random signing secret, at least 32 characters |
| `DATABASE_URL` | Defaults to `sqlite:///./data/campus.db` |
| `APP_TIMEZONE` | Campus timezone; defaults to `Africa/Nairobi` (UTC+03:00) |
| `MEDIA_DIR` | Private local media directory; defaults to `./data/media` |
| `GEMINI_API_KEY` | Server-side Gemini API credential |
| `GEMINI_MODEL` | Configurable Gemini model name |
| `CAMPUS_EMAIL_DOMAINS` | Optional comma-separated allowed email domains |
| `CORS_ORIGINS` | JSON array, for example `["http://localhost:3000"]` |
| `ACCESS_TOKEN_MINUTES` | Access-token lifetime, default 30 |
| `MAX_UPLOAD_BYTES` | Per-file limit, default 10 MiB, maximum 20 MiB |

For PostgreSQL, create a database and configure `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/campus`, then run `alembic upgrade head`.

The database is selected through configuration, not hardcoded into the routes. SQLite is the local default while the recipient decides on their deployment database. SQLAlchemy provides the relational database interface, and Alembic creates the schema in the selected database.

| Database | Example `DATABASE_URL` | Driver setup |
| --- | --- | --- |
| SQLite | `sqlite:///./data/campus.db` | Included with Python |
| PostgreSQL | `postgresql+psycopg://user:password@localhost:5432/campus` | Included in project dependencies |
| MySQL | `mysql+pymysql://user:password@localhost:3306/campus` | Run `pip install -e '.[mysql]'` |

Create the chosen database, update `.env`, and run `alembic upgrade head` against that database. Use MySQL 8.0.16 or newer so check constraints are enforced. PostgreSQL and MySQL still need integration testing against the actual server chosen by the recipient. Changing the URL selects a different database; it does not copy existing records or media. MongoDB or another nonrelational database would require a separate persistence implementation.

## Local timestamps

`APP_TIMEZONE=Africa/Nairobi` makes report and message timestamps appear in East Africa Time, with an explicit `+03:00` offset. Dates submitted without an offset are interpreted in that campus timezone. Dates submitted with an offset are converted to the same campus timezone in API responses. For example, both `2026-10-19T10:00:00` and `2026-10-19T07:00:00Z` return `2026-10-19T10:00:00+03:00`.

The database normalizes instants to UTC before storage, including on SQLite, which does not preserve timezone offsets. API responses convert them back to the configured campus timezone. JWT expiry calculations also use UTC internally. This keeps local display consistent even if the server is hosted in another country. Change `APP_TIMEZONE` to another IANA timezone and restart the application when deploying for another campus. This follows SQLAlchemy's [timezone normalization pattern](https://docs.sqlalchemy.org/en/21/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc).

## API reference

All paths below have the `/api/v1` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Register with email, name, and password |
| POST | `/auth/login` | Form fields `username` (email) and `password` |
| GET | `/auth/me` | Current account |
| POST / GET | `/items` | Create or browse reports |
| GET / PATCH / DELETE | `/items/{id}` | Read, edit, resolve, or delete a report |
| POST / GET | `/items/{id}/media` | Upload one multipart `file` or list media |
| GET / DELETE | `/media/{id}` | Download or delete media |
| POST / GET | `/items/{id}/matches` | Generate or read saved suggestions |
| POST | `/search/ai` | Natural-language AI search |
| POST / GET | `/conversations` | Start a conversation or list your conversations |
| POST / GET | `/conversations/{id}/messages` | Send or retrieve private messages |

Item browsing accepts `kind`, `status`, `category`, `q`, `mine`, `offset`, and `limit`. The default status filter is `open`; message and conversation lists also support offset/limit pagination. Messages are returned oldest first and can be polled by a future frontend.

Example report body:

```json
{
  "kind": "lost",
  "title": "Black laptop bag",
  "description": "A black laptop bag with a red zip and a small blue patch.",
  "category": "bags",
  "location": "Campus library, second floor",
  "occurred_at": "2026-10-19T10:00:00+03:00"
}
```

Use `PATCH /items/{id}` with `{"status":"resolved"}` after returning the item. Owners can reopen reports with `{"status":"open"}`. Start a conversation using `{"item_id":"..."}` and send a message using `{"body":"..."}`.

For AI search, send `{"description":"Black laptop bag with red zip","kind":"found"}` to `/search/ai`. An optional `category` filters the candidate pool. For image-based matching, attach a picture to your report and call `POST /items/{id}/matches`.

## Matching behavior and privacy

The service considers the latest 100 eligible open reports, ranks them by keyword overlap, and sends up to eight candidates to Gemini. Report matching excludes your own reports and compares lost reports with found reports. One image per report is resized to at most 768 pixels for the model. Results include candidate IDs, similarity scores, and reasons. IDs are checked against the candidate list, and suggestions below 0.4 are discarded. Scores are model suggestions, not calibrated probabilities or proof of ownership. This bounded search can miss older or poorly described reports.

The integration uses Google's official [Gen AI Python SDK](https://googleapis.github.io/python-genai/) with structured JSON responses.

Editing a report or changing its media invalidates saved matches involving that report. Deleting a report also deletes its conversations and messages. Account emails and password hashes are never included in public report responses or Gemini prompts. Gemini receives the descriptions, locations, dates, and attached images used in matching; tell users this before offering the feature and avoid personal details in reports.

## Upload handling

JPEG, PNG, and WebP images are decoded and re-encoded as JPEG to remove metadata and reject invalid images. MP4 and WebM uploads have their container signatures checked; videos are stored and downloadable but are not analyzed by AI in this version. A matching signature does not establish that an entire video is valid or safe: add a media scanner/transcoder before public video hosting. Original filenames are discarded, and uploads are served as attachments behind authentication. Configure a reverse proxy request-body limit as well: the per-file application check happens after multipart parsing.

## Tests and maintenance

```sh
pytest -q
ruff check .
ruff format --check .
alembic check
```

Tests use temporary SQLite databases and mocked Gemini calls, so no API key or paid AI request is needed. A live Gemini call and PostgreSQL integration need separate verification in the recipient's environment.

For schema changes, update the models, run `alembic revision --autogenerate -m "describe change"`, review the migration, then run `alembic upgrade head`. Back up the database and media directory together.

## Deployment scope

This version is suitable for local development and evaluation. Run a single application worker while using its in-memory request limiter. Multiple workers or replicas require a shared limiter such as Redis. Serve HTTPS through a reverse proxy, keep `.env` private, and persist the database/media directory. Campus domain filtering checks the email suffix only; it does not verify campus membership. Email verification, password recovery, user blocking/moderation, malware scanning, shared rate limiting, and production monitoring remain deployment work.

To use Docker, build this directory, pass configuration with `--env-file .env`, mount persistent storage at `/service/data`, and run `alembic upgrade head` in the configured container before starting the API. Docker packaging is supplied but requires verification on your target host.
