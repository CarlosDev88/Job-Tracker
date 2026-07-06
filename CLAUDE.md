# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal job-search tracker: imports job postings from multiple sources, filters them through a keyword/section-aware scoring pipeline against a candidate profile, and lets the user manually convert the ones worth pursuing into tracked applications in SQLite, moving through a Kanban-like pipeline of estados. An LLM-based semantic second pass exists in the backend but is currently disconnected from the UI (see below) — the Dashboard is a single manual-review ranking now, not a two-button pipeline.

## Commands

Backend (from repo root, `.venv` must exist — `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`):
```bash
./buscar.sh --listar-perfiles          # list profiles
./buscar.sh --perfil "Nombre"          # activate a profile
./buscar.sh --filtrar                  # Etapa 1: raw_data/*.json -> keyword/section filter -> filtradas/filtradas.json
./buscar.sh --analizar                 # Etapa 2: filtradas.json -> LLM semantic filter -> DB (backend-only now, not wired to the UI)
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

**Data flow:**

```
raw_data/*.json ──► Etapa 1: filtrar_raw_data() ──► filtradas/filtradas.json ──► user reviews cards on Dashboard
                    (backend/pipeline.py)          (ranked, overwritten            ──► clicks "Aplicar" per vacante
                                                     every run, not persisted           ──► POST /pipeline/aplicar
                                                     to DB)                                ──► job_applications (estado=aplicado)
```

Etapa 1 (`POST /pipeline/filtrar`) is free (no LLM) and writes the full ranking to `filtradas/filtradas.json`, exposed via `GET /pipeline/filtradas` and rendered as a paginated (10/page) card grid on the Dashboard — this file is a working buffer, not history, fully overwritten every run and never inserted into SQLite on its own. The user reviews cards (title, company, score/decision badge, image thumbnails for feed posts) and, per vacante, opens a detail popup with four actions: **Copiar empleo** (clipboard), **Hacer CV con IA** (UI placeholder, no logic yet), **Ir a la vacante** (opens the real posting/profile link), and **Aplicar** (`POST /pipeline/aplicar` → `pipeline.py::convertir_a_oferta` → `create_aplicacion` + `update_estado(..., "aplicado")`, inserted straight into `job_applications` with no LLM involved).

The old two-stage "Etapa 2" LLM semantic pass (`analizar_con_llm`, `POST /pipeline/analizar`, the `filtrar_con_llm` prompt) is **still implemented but disconnected from the frontend** — no button calls it anymore. It's a candidate for reuse (or removal) later; don't assume it runs as part of the normal flow.

**Sources land in `raw_data/` in four different shapes**, all produced by the user's own scrapers (not code in this repo) with a consistent filename convention that `pipeline.py::_detectar_fuente` reads to set `fuente`:
- `linkedin_*.json` → `linkedin_extension` — already standard shape (`titulo`, `empresa`, `ubicacion`, `descripcion`, `link`).
- `getonbrd_*.json` → `getonbrd` — same standard shape.
- `linkedin_publicaciones_*.json` → `linkedin_publicaciones` — same standard shape.
- `linkedin_feed_*.json` → `linkedin_feed` — a different, noisy shape: most items are ordinary feed posts unrelated to jobs; a small minority carry an embedded `tarjeta_empleo` object and an `imagenes` array (post photos/flyers), and some announce a job in free text with no structured card at all.

**`backend/filtros/normalizador.py::normalizar_vacante(item, fuente)`** is the adapter that reconciles this. The `fuente` (from the filename, not the item's shape) is what gates the logic:
- `fuente != "linkedin_feed"` → item is already vacante-shaped, returned unchanged (still carries `imagenes` through if present).
- `fuente == "linkedin_feed"` and `tiene_tarjeta_empleo` is true → map fields out of the embedded `tarjeta_empleo`.
- `fuente == "linkedin_feed"` and no tarjeta → delegates entirely to `backend/filtros/feed_filter.py::clasificar_post_feed` (see below) instead of the generic keyword filter.

**`backend/filtros/feed_filter.py`** is a *separate, dedicated* filter for linkedin_feed posts without a structured tarjeta — the generic filter in `keywords.py` doesn't work well on a short feed caption, and an earlier attempt to relax `keywords.py`'s thresholds for these posts let through real noise (celebration posts, birthday posts, "proud to announce" posts all incidentally match loose keyword/image heuristics). The algorithm (spec in `algoritmo_feed.md`):
1. Unicode-normalizes text (NFKD, strip accents, lowercase) — LinkedIn posts are frequently written in stylized bold Unicode (`𝐒𝐨𝐟𝐭𝐰𝐚𝐫𝐞`) that plain `.lower()` doesn't fold to matchable ASCII.
2. Requires **two signals**, not one: a hiring-language signal (`SENAL_CONTRATACION`: "buscamos", "hiring"...) *and* an application/contact signal (`SENAL_APLICACION`, an email regex, or an `lnkd.in` link) — this is what filters out "buscamos mejorar nuestros procesos"-style false positives.
3. Scores stack fit (`CORE`/`SECUNDARIO` additive, `VETO` list rejects outright — e.g. NestJS, Kubernetes, Angular unless React is also mentioned).
4. Classifies `REVISAR` (score ≥ `UMBRAL_REVISAR`) or `TAL_VEZ` (≥ `UMBRAL_TALVEZ`), extracting any email/link found as contact info. Both tiers survive into `filtradas.json` with `revisar_manual: True` — no titulo/empresa extraction (no LLM call spent on that), the frontend shows a `DecisionBadge` (REVISAR=green/TAL_VEZ=yellow) instead of the percentage `ScoreBadge`, plus the extracted emails/links in the detail popup. Deduplication across scrape files happens in `pipeline.py::filtrar_raw_data` (a `vistos_feed` set keyed on normalized caption text), since feed posts commonly repeat across scrape runs.

**Etapa 1 for non-feed vacantes** runs through `backend/filtros/keywords.py::filtrar_vacante` (rewritten per `algoritmo_feed.md`'s sibling spec for regular postings — same design philosophy, title-weighted and section-aware):
1. Hard blacklist (regex on WordPress, Drupal, Spring Boot, ASP.NET, C#, Joomla, Odoo, COBOL — unconditional, any section) → immediate reject.
2. `VETO_IDIOMA`: advanced/fluent/C1 English required → immediate reject **regardless of location** (this used to only reject for remote US/Europe; validated against real postings that it should reject unconditionally).
3. `_veto_ubicacion`: on-site/hybrid role outside Bucaramanga with no remote mention → immediate reject.
4. `_veto_stack` (`VETO_DURO_PATTERNS`): incompatible stacks (NestJS, Kubernetes, Kafka, RabbitMQ, Terraform, PHP, Laravel, .NET, Java/Python backend, React Native, Angular-without-React, Supabase, Prisma, Shopify/Liquid, DynamoDB family) reject **only if found in the "requisitos duros" section** of the text (`_mapa_zonas`/`_zona_en` locates DURO vs BLANDO headers); the same keyword in a "deseable" section is informational only (`gaps_blandos`), doesn't reject.
5. `calcular_score` (0-100): CORE keywords (react/next.js/typescript/frontend/vtex) in the **title** score double (+15 each, capped at +30) vs. in the requisitos-duros body (+8); SECUNDARIO (+3) and BONUS_PERFIL (+5, e-commerce/retail/performance/lighthouse/i18n) score anywhere; profile's own `keywords_incluir`/`keywords_excluir` (from the `perfiles` table) still apply on top (+5/-30) so multi-profile behavior isn't lost; "3-4 años" experience mentions add +5, "6+ años" subtracts 10 (assumes candidate has 5); a flat +5 applies for non-advanced English (since advanced already rejected above); remote+LATAM/Colombia adds +5.
6. Four-tier classification: `score >= 55` → `APLICAR_YA`, `35-54` → `APLICAR`, `20-34` → `REVISAR_MANUAL` (still survives into filtradas.json — this is the "pass it to me" tier, not a silent reject), `< 20` → discarded.

**LLM connectors** (`backend/llm/`): `base.py` defines the `LLMConnector` interface (`generar(prompt) -> str`, `enabled: bool`), `factory.py` picks a connector based on `LLM_PROVIDER` in `.env` (**`gemini` is the default** — cost-driven switch from Claude; `claude_connector.py` still works if you set `LLM_PROVIDER=claude`). `gemini_connector.py` throttles itself to 15 requests/minute via a module-level (not instance-level) sliding-window queue, since `get_connector()` creates a fresh instance per call — the free tier's real constraint is actually a **daily** quota (~20 requests/day for `gemini-2.5-flash`), which the RPM throttle doesn't prevent; a quota-exceeded error is detected by `llm_filter.py` (`error: True, cuota_agotada: True`) and `analizar_con_llm` stops the batch early rather than burning through remaining candidates on guaranteed failures. This whole path is currently unused by the UI (see above) but kept working.

**Perfiles** (`perfiles` table) hold the candidate's include/exclude keywords, CV text, and per-source search config. Only one perfil is `activo` at a time (`activar_perfil` unsets all others first) — the pipeline always operates against `get_perfil_activo()`. Note: `feed_filter.py`'s CORE/SECUNDARIO/VETO lists and `keywords.py`'s Bucaramanga location check are hardcoded for the single active user profile, not yet driven by a per-profile field.

**Backend** (`backend/`): FastAPI app (`main.py`), no ORM — `database.py` wraps raw sqlite3 with `Row` factory, functions returning plain dicts. `run.py` is the CLI entry point (used by `buscar.sh`).

**Frontend** (`frontend/`): React + Vite + Tailwind, three routes (`Dashboard`, `Ofertas`, `Perfiles`) defined in `App.jsx`, talking to the backend through the `/api` Vite proxy (`vite.config.js` — proxy target is `VITE_API_TARGET`, defaulting to `localhost:8000`, overridden to `http://backend:8000` inside Docker). Shared badge components live in `frontend/src/components/` (`ScoreBadge` for percentage scores, `DecisionBadge` for the feed's REVISAR/TAL_VEZ labels).

**job_applications.estado** is a fixed pipeline enforced in `database.py::update_estado`: `pendiente → aplicado/cv_enviado → hr_contacto → prueba_tecnica → entrevista_rrhh → entrevista_tecnica → oferta`, with `rechazado`/`ghosted` as terminal off-ramps. Setting estado to `aplicado` or `cv_enviado` auto-stamps `fecha_aplicacion`.

## Notable conventions

- All domain terms are in Spanish (perfiles, vacantes, aplicaciones, estado, filtradas) — keep new code consistent with this rather than mixing English.
- Comments are kept minimal by design: only where they explain a non-obvious "why" (a regex gotcha, a safety constraint, a business-logic reason) — not restating what the code already says. Section-divider comments and restated-code comments have been deliberately removed; don't reintroduce them.
- Secrets and per-machine config (`LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `RAW_DATA_PATH`, `RAW_DATA_HOST_PATH`) are loaded from `.env` via `python-dotenv`; `.env.example` is the tracked template since `.env` itself is gitignored.
- There is no `backend/scrapers/` anymore — GetOnBord live-scraping and the Playwright LinkedIn stub were removed. Job data only ever enters via `raw_data/*.json` files (dropped there by external scrapers the user runs separately, not by this codebase).
