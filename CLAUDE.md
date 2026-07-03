# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal job-search tracker: imports job postings from multiple sources, filters them through a two-stage pipeline (keyword scoring, then an LLM semantic check) against a candidate profile, and stores the survivors in SQLite for tracking application status through a Kanban-like pipeline of estados.

## Commands

Backend (from repo root, `.venv` must exist — `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`):
```bash
./buscar.sh --listar-perfiles          # list profiles
./buscar.sh --perfil "Nombre"          # activate a profile
./buscar.sh --filtrar                  # Etapa 1: raw_data/*.json -> keyword filter -> filtradas/filtradas.json
./buscar.sh --analizar                 # Etapa 2: filtradas.json -> LLM filter -> DB
./buscar.sh --importar                 # both stages back to back
uvicorn backend.main:app --reload --port 8000   # run the API server directly
```
There are no automated tests or linters configured in this repo.

Frontend (from `frontend/`, uses pnpm):
```bash
pnpm install
pnpm dev       # Vite dev server on :5173, proxies /api -> http://localhost:8000
pnpm build
pnpm preview
```

Docker (from repo root, needs Docker Desktop with WSL integration enabled):
```bash
docker compose up --build   # starts backend (:8000) + frontend (:5173) together
```
`raw_data/` is bind-mounted from `RAW_DATA_HOST_PATH` (set in `.env`) — point it at wherever the Chrome extension drops its JSON exports (e.g. a Windows Downloads folder, visible from WSL as `/mnt/c/...`) and files show up in the container with zero manual copying. The sqlite file persists in a named volume (`db_data`), not a bind mount.

## Architecture

**Data flow — two manual stages, not one automatic pipeline:**

```
raw_data/*.json ──► Etapa 1: filtrar_raw_data() ──► filtradas/filtradas.json ──► Etapa 2: analizar_con_llm() ──► DB
                    (backend/pipeline.py)          (ranked, overwritten          (backend/pipeline.py)
                                                     every run)
```

This split is deliberate: Etapa 1 (keyword filter) is free and lets you eyeball the ranked results before spending LLM calls in Etapa 2. In the frontend Dashboard these are two separate buttons ("1. Filtrar vacantes" / "2. Analizar con IA"); the ranking is shown between them. `POST /pipeline/filtrar` and `POST /pipeline/analizar` are the corresponding endpoints.

**Sources land in `raw_data/` in four different shapes**, all produced by the user's own scrapers (not code in this repo) with a consistent filename convention that `pipeline.py::_detectar_fuente` reads to set `fuente`:
- `linkedin_*.json` → `linkedin_extension` — already standard shape (`titulo`, `empresa`, `ubicacion`, `descripcion`, `link`).
- `getonbrd_*.json` → `getonbrd` — same standard shape.
- `linkedin_publicaciones_*.json` → `linkedin_publicaciones` — same standard shape.
- `linkedin_feed_*.json` → `linkedin_feed` — a different, noisy shape: most items are ordinary feed posts unrelated to jobs; a small minority carry an embedded `tarjeta_empleo` object, and some announce a job in free text with no structured card at all.

**`backend/filtros/normalizador.py::normalizar_vacante(item, fuente)`** is the adapter that reconciles this. The `fuente` (from the filename, not the item's shape) is what gates the logic:
- `fuente != "linkedin_feed"` → item is already vacante-shaped, returned unchanged. No regex, no LLM call, regardless of what the text says.
- `fuente == "linkedin_feed"` and `tiene_tarjeta_empleo` is true → map fields out of the embedded `tarjeta_empleo`.
- `fuente == "linkedin_feed"` and no tarjeta → a cheap regex (`PALABRAS_CONTRATACION`) is a broad first pass; only regex hits get a short LLM call asking "is this actually a job posting, and if so what's the titulo/empresa/ubicacion" — plain keyword matching alone produces too many false positives here (validated against real data: 11/80 feed posts matched hiring keywords, only ~2 were real postings — the rest were `#OpenToWork` self-promotion, recruiting-platform ads, and hashtag spam). Since there's no real job link in this case, `autor_perfil` (the poster's LinkedIn profile) is used as a fallback `link`.

**Etapa 1** (`filtrar_raw_data`) runs every normalized vacante through `backend/filtros/keywords.py::filtrar_vacante`, which implements the algorithm in `spec.md`:
1. Hard blacklist (regex on WordPress, Drupal, Spring Boot, ASP.NET, C#, etc.) → immediate reject.
2. Inglés avanzado/fluido + remoto US/Europa → immediate reject (`clasificar_ingles`).
3. `STACK_AUSENTE_PESO`: weighted "gap" tracking for stacks not covered (NestJS, Kubernetes, Kafka, Terraform, Supabase, PHP, Java/Python backend, React Native producción, Azure AD/Entra). Each gap is classified DURO or BLANDO by which section marker (`requisitos`/`indispensable` vs `deseable`/`plus`) precedes it in the text (`_mapa_zonas`/`_zona_en`) — only DURO gaps count toward the reject threshold (sum >= 3); BLANDO gaps are informational only (`gaps_blandos`). A "X+ años" mention near a gap adds +2 severity.
4. Score (`calcular_score`, global `WEIGHTS` dict + profile's own `keywords_incluir`/`keywords_excluir`) must be >= 20.
Survivors get a `decision` of `APLICAR` or `APLICAR_CON_RESERVA` (if there are gaps_blandos or riesgo_ingles MEDIO), get written into `filtradas.json` sorted by score descending — this file is fully overwritten on every run, it's a working buffer, not history.

**Etapa 2** (`analizar_con_llm`) reads `filtradas.json` and runs `backend/filtros/llm_filter.py::filtrar_con_llm`, which builds the semantic-fit prompt and delegates the actual call to whichever LLM connector is configured — this part is provider-agnostic. Survivors are inserted into `job_applications`, deduped by `link` (normalized — query string and trailing slash stripped before the uniqueness check, so tracking-parameter variants of the same URL don't slip through as duplicates).

**LLM connectors** (`backend/llm/`): `base.py` defines the `LLMConnector` interface (`generar(prompt) -> str`, `enabled: bool`), `factory.py` picks a connector based on `LLM_PROVIDER` in `.env` (`claude` is the default; `gemini` is fully implemented too). `claude_connector.py` uses the `anthropic` SDK, model `claude-sonnet-5`, `output_config: {"effort": "low"}`. `chatgpt_connector.py` is a placeholder (raises `NotImplementedError`) for when that's needed. Every connector degrades gracefully when its API key is unset — `enabled = False`, and `filtrar_con_llm` treats that as an automatic pass (`pasa: True`, "sin API key configurada — skipped") rather than erroring.

**Perfiles** (`perfiles` table) hold the candidate's include/exclude keywords, CV text, and per-source search config. Only one perfil is `activo` at a time (`activar_perfil` unsets all others first) — the pipeline always operates against `get_perfil_activo()`.

**Backend** (`backend/`): FastAPI app (`main.py`), no ORM — `database.py` wraps raw sqlite3 with `Row` factory, functions returning plain dicts. `run.py` is the CLI entry point (used by `buscar.sh`).

**Frontend** (`frontend/`): React + Vite + Tailwind, three routes (`Dashboard`, `Ofertas`, `Perfiles`) defined in `App.jsx`, talking to the backend through the `/api` Vite proxy (`vite.config.js` — proxy target is `VITE_API_TARGET`, defaulting to `localhost:8000`, overridden to `http://backend:8000` inside Docker).

**job_applications.estado** is a fixed pipeline enforced in `database.py::update_estado`: `pendiente → aplicado/cv_enviado → hr_contacto → prueba_tecnica → entrevista_rrhh → entrevista_tecnica → oferta`, with `rechazado`/`ghosted` as terminal off-ramps. Setting estado to `aplicado` or `cv_enviado` auto-stamps `fecha_aplicacion`.

## Notable conventions

- All domain terms are in Spanish (perfiles, vacantes, aplicaciones, estado, filtradas) — keep new code consistent with this rather than mixing English.
- Comments are kept minimal by design: only where they explain a non-obvious "why" (a regex gotcha, a safety constraint, a business-logic reason) — not restating what the code already says. Section-divider comments and restated-code comments have been deliberately removed; don't reintroduce them.
- Secrets and per-machine config (`LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `RAW_DATA_PATH`, `RAW_DATA_HOST_PATH`) are loaded from `.env` via `python-dotenv`; `.env.example` is the tracked template since `.env` itself is gitignored.
- There is no `backend/scrapers/` anymore — GetOnBord live-scraping and the Playwright LinkedIn stub were removed. Job data only ever enters via `raw_data/*.json` files (dropped there by external scrapers the user runs separately, not by this codebase).
