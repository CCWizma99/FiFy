# FiFy — Fashion Search

FiFy combines a React/Vite frontend with a FastAPI backend, CLIP embeddings,
Qdrant vector storage, and a Playwright crawler using Gemini to analyze layouts.

## Development setup

Use Python 3.11+ (the lock is validated on Python 3.12) and Node.js 22.12+ or 24.
Run commands from the existing repository checkout.

```sh
python -m venv .venv
. .venv/bin/activate                    # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
cd frontend
npm ci
cd ..
```

`pyproject.toml` is the dependency source. `requirements.lock` contains generated
pins including the `dev` extra, and `requirements.txt` includes that lock.
The currently imported `google-generativeai` SDK is retained; protobuf is bounded
below version 6 for compatibility. The SDK is deprecated upstream; migration is
separate work. To refresh pins intentionally with uv:

```sh
uv pip compile pyproject.toml --extra dev -o requirements.lock
```

## Startup and configuration

For live application use, copy `.env.example` to `.env` and replace its placeholder
Qdrant URL/key and Google API key with your own configuration. Never commit secrets.
The backend can start without these credentials, but catalog/search/crawler operations
need the relevant services. SQLite files under `data/` are initialized on startup.

```sh
fify-backend
# Equivalent: python run_server.py
```

Both entry points use `API_HOST`/`API_PORT` from environment or `.env` (defaults
`0.0.0.0:8000`), with reload disabled and the asyncio event loop for Playwright.

In a second terminal:

```sh
cd frontend
npm run dev
```

Set `VITE_API_URL` in `frontend/.env.local` for a custom backend address. The default
is `http://localhost:8000`. Absolute URLs such as `https://api.example/api/` and
same-origin relative prefixes such as `/api/` work for search, admin HTTP, image
proxy URLs, and crawler WebSockets. HTTPS uses `wss:`. A reverse proxy must forward
that prefix, support WebSocket upgrades, and serve SPA routes through `index.html`.
Cross-origin deployments must also configure the backend's allowed CORS origins.

Live crawling additionally requires `python -m playwright install chromium` and
Chromium's system libraries. CLIP weights download on first embedding use. These
external operations are not part of the default local checks below. Initialize a
configured Qdrant collection only when intentionally preparing a live catalog:

```sh
python -c "from vector_db.schema import create_collection; create_collection()"
```

## Local checks (no external services)

```sh
python -m pytest
uv pip check --python .venv/bin/python
cd frontend
npm test
npm run lint
npm run build
```

Python tests exercise API validation with in-process ASGI requests and mocked
application services, scraper profile persistence/migration, and the CLI with
`uvicorn.run` mocked. Default Python tests block outbound socket connections.
Frontend tests use mocked fetch, WebSocket, storage, and sharing responses.

Model-download tests are explicitly opt-in and require model access/cache:

```sh
python -m pytest -o addopts= -m model_download tests/test_embedding.py
```

No model-download tests or live Qdrant, CLIP, Gemini, or retailer requests are needed
for normal development validation.

## UI behavior

Home sorts only its loaded selection, not the whole catalog. Favorites are local to
this browser, shared across Home, Results, product detail, and `/saved`. If browser
storage fails, favorites remain available for the current session. Sharing uses
native sharing where available, then the clipboard, with visible failure messages.
About, Privacy, Terms, and Contact pages explain the app and link to the issue tracker.
There is no account, subscription, or price-history service.

## FiFy AI Assistant and reusable widget

The floating assistant appears on public FiFy pages. It answers from 15 approved
FAQs in `backend/chatbot/fify_chatbot_knowledge.json`, with live Gemini responses.
It cannot search live inventory, process payments, track orders, or verify retailer
policies. This is a small FAQ prompt, **not RAG**. No chat conversations are stored
by the application. The panel includes a visible sensitive-data warning.

The new assistant uses `google-genai`, isolated from the crawler's existing
`google-generativeai` SDK. Both are pinned in the shared dependency lock. It reuses
the **server-only** `GOOGLE_API_KEY`; never use a `VITE_*` variable for a credential.
The managed environment HTTP secret destination is `generativelanguage.googleapis.com`.
`GEMINI_MODEL` selects the chatbot model (default `gemini-2.5-flash`), independently
of the scraper's `GEMINI_MODEL_NAME`.

Start the full app with the usual `fify-backend` / `python run_server.py` and
`npm run dev` commands. The UI loads `/widget.js` from `VITE_API_URL` and the iframe
calls the API on its own origin, so embedding does not require opening CORS to
arbitrary websites. Set `API_PORT` and `VITE_API_URL` together when overriding ports.
For chatbot-only development without importing CLIP, Qdrant, or the crawler:

```sh
python -m uvicorn backend.chatbot.app:app --host 127.0.0.1 --port 8010
```

The independent HTML demo is served at `/embed-test.html` on the backend. It has
no React or npm dependency. A website on the **same origin** needs just:

```html
<script src="/widget.js" data-bot-id="fify-demo" defer></script>
```

A different website must use an absolute script URL. For example, while testing
locally against the backend on port 8010:

```html
<script src="http://127.0.0.1:8010/widget.js"
        data-bot-id="fify-demo"
        data-title="FiFy AI Assistant"
        data-theme="#142542"
        defer></script>
```

This local URL is a development example, not a public deployment. No hosting origin
has been approved. After deployment approval, replace the script origin with the
actual HTTPS host. `data-bot-id` is public configuration, not authentication.
`data-title` changes the header; `data-theme` takes a six-digit hex color (use a dark
color for readable white text). The iframe isolates the widget from host CSS.
The host's CSP must allow the script and iframe origin. Reverse proxies must serve
`/widget.js`, `/chatbot/*`, and `/api/chatbot/message` under the same backend prefix.

### Limits and privacy

`POST /api/chatbot/message` validates a `bot_id` of `fify-demo`, a nonempty message
of at most 1,000 characters, and at most 8 recent user/assistant turns (1,000 characters
per turn). Bodies over 16 KiB are rejected before JSON parsing. Model output is
limited to 800 tokens and 2,000 displayed characters, with a 25-second server deadline.
Missing configuration, quota exhaustion, timeouts, and upstream failures return
explicit 503/429/504/502 errors; there are no fake fallback answers.

The default budget is **8 requests per IP per UTC minute** and **100 requests total
per UTC day**, including failed upstream attempts. Configure `CHATBOT_RATE_LIMIT`,
`CHATBOT_DAILY_LIMIT`, and `CHATBOT_USAGE_DB` for the demo. The SQLite file stores
only counters and salted client hashes, not raw addresses or conversation text.
Keep this database on persistent storage across restarts and shared by workers on
the same machine. Separate replicas need a shared limiter before public deployment;
SQLite on separate hosts would not enforce one global cap. Configure a reverse proxy
and Uvicorn to trust forwarded client IPs only from that known proxy. Do not trust
arbitrary client `X-Forwarded-For` headers. Protect or remove the pre-existing admin
routes before exposing the full app publicly; the chatbot-only app has no admin routes.
This implementation does not grant approval for a public deployment or paid hosting.

### Tests and gallery capture

Normal `pytest` and `npm test` mock Gemini and never require real model calls.
New tests cover API validation, safe errors, persistent limits, style isolation,
input, reset, retries, late responses, and mounting on public pages.
To intentionally run a real-key browser smoke and capture three authentic
1280 × 769 PNG screenshots:

```sh
# Start backend on 8010 and frontend on 5173 with VITE_API_URL=http://127.0.0.1:8010.
# Install Playwright Chromium once if needed.
python scripts/chatbot_demo.py --live --output /tmp/fify-gallery
```

This opt-in command makes three real Gemini calls and consumes quota. It verifies
photo-search guidance, favorites guidance, a separate one-script HTML integration,
and mobile open/close/reset. It saves only the explicitly chosen public demo
questions/answers beside the screenshots for provenance. Do not capture personal
conversations or credentials. The default application does not persist chat history.
