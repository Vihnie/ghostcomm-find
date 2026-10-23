# GhostComm Find

A campus lost-and-found platform with a React/Vite frontend and a FastAPI backend. The interface uses real authenticated API requests for registration, sign-in, report search, report editing/resolution, media uploads, Gemini matching, and private messages. The original landing-page design is preserved.

## Database plan

The browser calls FastAPI; FastAPI connects to the database. Database credentials, JWT secrets, and Gemini API keys must stay on the backend.

For local development, SQLite is the default and creates a persistent file at `backend/data/campus.db`. You do not need a database account to run the project. This file and uploaded media are excluded from Git. GitHub stores the source code and migrations, not the running database.

For deployment, choose a relational database and set `DATABASE_URL` in the backend host's private environment settings. PostgreSQL is supported with the included driver; MySQL has an optional driver. Create the database first, then run `alembic upgrade head` against it. Test the selected server before deployment. Changing the URL does not migrate existing SQLite records: transfer any data you need separately, and transfer media files too.

```env
# Local backend/.env
DATABASE_URL=sqlite:///./data/campus.db
APP_TIMEZONE=Africa/Nairobi
```

```env
# Example hosted PostgreSQL backend environment; use your provider's real connection URL
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

## Backend setup

Requires Python 3.11 or newer. From the project root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Set `JWT_SECRET` in `backend/.env` to the generated secret. Leave `GEMINI_API_KEY` empty until you have a key; reports and communication work without it. AI requests return a configuration message until a key is provided.

```sh
mkdir -p data
alembic upgrade head
uvicorn app.main:create_app --factory --reload --port 8010
```

Windows PowerShell equivalents for creating the environment are `py -3 -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, and `Copy-Item .env.example .env`. Create the data directory with `New-Item -ItemType Directory -Force data`, then use the same migration and Uvicorn commands.

API documentation: [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs).

## Frontend setup

In a second terminal, from the project root:

```sh
npm ci
npm run dev -- --host 127.0.0.1
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173), or the port Vite prints if 5173 is in use. The development proxy forwards `/api` requests to `http://127.0.0.1:8010`. Both processes must be running.

Optional root `.env` settings can be copied from `.env.example`:

```env
VITE_API_BASE_URL=/api/v1
API_PROXY_TARGET=http://127.0.0.1:8010
```

`API_PROXY_TARGET` configures only Vite's development server. `VITE_API_BASE_URL` is public frontend configuration; never put a secret in any `VITE_` variable.

Vite's [proxy documentation](https://vite.dev/config/server-options#server-proxy) describes how development requests are forwarded.

## Using the connected app

1. Select **Sign in or create an account**, then create an account with a password of at least 12 characters.
2. Browse actual reports, search by text, filter lost/found reports, or select **My reports**.
3. Select **Report lost or found**, save the details, and add pictures or a video in the detail dialog.
4. On your own reports, edit the details, find possible AI matches, mark resolved, reopen, or delete the report.
5. Open another user's report and select **Contact reporter**. Both people can reopen the conversation through **Messages**. Messages refresh every 10 seconds while open.
6. Use AI search with a description of at least 10 characters. AI search looks for found reports unless the Lost filter is selected. It considers open reports, independently of the regular status/My reports filters.

API timestamps include the configured campus offset; date/time inputs use campus local time. The session token is kept in the current browser tab's session storage, cleared on sign-out, and expires according to the backend token lifetime. Passwords are not stored by the frontend. Protect against cross-site scripting because browser JavaScript can access session storage.

Uploaded media is fetched using authenticated requests, so file links do not expose a public upload directory. AI matching shares report descriptions and attached images with Gemini only when requested. Suggestions do not prove ownership.

## Deployment

Build the frontend with `npm run build`. A Vite development proxy is not part of the production build. Either configure your production reverse proxy to forward `/api` to FastAPI, or set `VITE_API_BASE_URL=https://YOUR-BACKEND-HOST/api/v1` before building. For separate frontend/backend domains, set backend `CORS_ORIGINS` to a JSON array containing the exact frontend origin, for example `["https://YOUR-FRONTEND-HOST"]`.

Configure `DATABASE_URL`, a private `JWT_SECRET`, `APP_TIMEZONE`, and optional `GEMINI_API_KEY` on the backend host. Keep uploads on persistent storage and run migrations before starting the backend. Review [backend deployment limitations](backend/README.md#deployment-scope), including shared rate limiting, email verification, password recovery, and video scanning, before public use. Live Gemini and PostgreSQL/MySQL need verification with the recipient's credentials.

## Validation

```sh
npm test
npm run lint
npm run build
```

From `backend` with its environment active:

```sh
pytest -q
ruff check .
ruff format --check .
alembic check
```

See [backend documentation](backend/README.md) for the endpoint reference and database configuration details.

## Combined Render demo

The repository-root `Dockerfile` builds React and serves the built website from FastAPI at the same URL as `/api/v1`. In Render, clear the service Root Directory, use `./Dockerfile`, and set the Docker Build Context Directory to `.`. Existing backend-only Docker builds under `backend/` still work independently. The root image respects Render's `PORT` variable and initializes the database on startup.

For a shared demo database, set the backend's private `DATABASE_URL` to a PostgreSQL URL using the installed driver: `postgresql+psycopg://...`. Use the database's internal connection details when hosted in the same Render region. Never put this URL in a frontend variable or commit it. Render's free PostgreSQL database expires after 30 days. This deployment is a free demonstration, not durable production hosting.

The current image stores uploaded media locally. On Render Free, those files can disappear after a restart, redeploy, or idle spin-down. A shared PostgreSQL database preserves accounts, descriptions, and messages independently of the app instance, but permanent uploads still require separate object storage. AI matching also needs a valid backend `GEMINI_API_KEY`; it is optional for ordinary reports and messages.

Without `FRONTEND_DIR`, local backend development retains the JSON status endpoint at `/`. The combined image sets `FRONTEND_DIR=/service/frontend` so `/` serves the actual website; `/health`, `/docs`, and `/api/v1` keep their existing behavior.
