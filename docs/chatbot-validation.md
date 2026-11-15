# FiFy assistant validation — 15 November 2026

## Passed

- Existing and new local Python tests: **35 passed, 4 model-download tests deselected**.
- Frontend tests: **30 passed**. Includes widget loading, input, keyboard controls,
  reset/abort, retry without duplicate turns, text-only rendering, resize-origin
  validation, and public/admin route mounting.
- `npm run lint` and `npm run build`.
- `uv pip check --python .venv/bin/python`: all installed packages compatible.
  Both Google SDKs coexist; the scraper SDK and behavior were not migrated.
- Real-key endpoint smoke: Gemini explained favorites and lack of accounts.
- Real-key grounding check: assistant declined order lookup, payment processing,
  and unverified live stock/prices.
- Real browser: full FiFy app + live assistant; independent plain HTML + one-script
  assistant; 375 × 812 mobile open/close/reset. No JavaScript page errors.
- Three 1280 × 769 PNG screenshots captured from actual Gemini conversations,
  with no fabricated responses, inventory, testimonials, or synthetic overlays.
- Chatbot-only FastAPI app and static routes are tested independently of catalog
  imports. Normal tests block outbound sockets and mock all AI calls.

## Gallery outputs

- `01-fify-assistant-hero.png`
- `02-live-conversation.png`
- `03-one-script-integration.png`

These are delivered as separate artifacts, not generated binaries in the repository.
The opt-in `scripts/chatbot_demo.py --live` command reproduces the gallery and saves
only its explicitly selected public demo transcript alongside the images.

## Runtime notes and scope

- The existing Home API CORS setting permits `http://localhost:5173`; the screenshot
  run used that frontend origin, backend port 8010, and the matching `VITE_API_URL`.
- This managed proxy requires an explicit HTTPS port 443 in the Qdrant URL used by
  the Qdrant Python client. The local full-app process used a runtime-only override;
  no Qdrant data, credentials, crawler code, or catalog logic was changed for this feature.
- The chatbot works without a populated catalog. Gallery imagery makes no stock or
  product availability claims.
- Existing upstream deprecation warnings remain (legacy Google SDK, pytest/anyio,
  and Browserslist data). They do not fail the verified checks.
- No hosting origin is approved; nothing was deployed or merged. Public deployment
  needs HTTPS, persistent/shared rate-limit storage, correctly trusted proxy IPs,
  and a restricted admin surface. The README documents the single-host demo limits.
- FAQ prompt grounding is implemented; vector retrieval/RAG is not advertised.
- No paid hosting, optional screen recording, or retailer crawling was performed.
