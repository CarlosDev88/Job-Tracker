# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal job-search tracker: scrapes/imports job postings, filters them against a candidate profile (keyword scoring + Gemini semantic check), and stores the survivors in SQLite for tracking application status through a Kanban-like pipeline of estados.

## Commands

Backend (from repo root, `.venv` must exist — `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`):
```bash
./buscar.sh --listar-perfiles          # list profiles
./buscar.sh --perfil "Nombre"          # activate a profile, scrape GetOnBord, run pipeline
./buscar.sh --importar                 # import raw_data/*.json (from the Chrome extension) through the pipeline
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

## Architecture

**Data flow**: job postings enter from two sources — the GetOnBord REST API (`backend/scrapers/getonbord.py`, called live via `POST /pipeline/run`) and a Chrome extension that scrapes LinkedIn manually and drops JSON files into `raw_data/` (processed via `POST /pipeline/importar-raw` or `./buscar.sh --importar`). `backend/scrapers/linkedin.py` (Playwright) is a stub for a planned automated scraper — not yet implemented.

Both sources funnel through `backend/pipeline.py::procesar_vacantes`, which always uses the currently active *perfil* (candidate profile):
1. **Filtro 0 — blacklist dura** (`filtros/keywords.py::blacklist_check`): regex hard-reject on stack keywords (Java, .NET, PHP, WordPress, etc.), carefully excluding false positives like "javascript" matching "java".
2. **Filtro 1 — scoring** (`filtros/keywords.py::calcular_score`): weighted keyword scoring (global `WEIGHTS` dict + profile's own `keywords_incluir`/`keywords_excluir`), normalized to 0-100. Needs score >= 20 to pass.
3. **Filtro 2 — Gemini semántico** (`filtros/gemini.py::filtrar_con_gemini`): only called when score passes, to conserve free-tier quota. Sends CV + vacante to `gemini-2.5-flash` for a pass/fail semantic judgment. If `GEMINI_API_KEY` is unset, this filter is a no-op (always passes).
4. Survivors are inserted into `job_applications` (deduped by unique `link`).

**Perfiles** (`perfiles` table) hold the candidate's include/exclude keywords, CV text, and per-source search config (`linkedin_search_string`, `getonbord_tags`). Only one perfil is `activo` at a time (`activar_perfil` unsets all others first) — the pipeline always operates against `get_perfil_activo()`.

**Backend** (`backend/`): single-file FastAPI app (`main.py`) with no ORM — `database.py` wraps raw sqlite3 with `Row` factory, functions returning plain dicts. `run.py` is a CLI entry point (used by `buscar.sh`) that wraps the same pipeline/database functions for headless/manual runs outside the API.

**Frontend** (`frontend/`): React + Vite + Tailwind, three routes (`Dashboard`, `Ofertas`, `Perfiles`) defined in `App.jsx`, talking to the backend through the `/api` Vite proxy (see `vite.config.js`).

**job_applications.estado** is a fixed pipeline of values enforced in `database.py::update_estado`: `pendiente → aplicado/cv_enviado → hr_contacto → prueba_tecnica → entrevista_rrhh → entrevista_tecnica → oferta`, with `rechazado`/`ghosted` as terminal off-ramps. Setting estado to `aplicado` or `cv_enviado` auto-stamps `fecha_aplicacion`.

## Notable conventions

- All domain terms are in Spanish (perfiles, vacantes, aplicaciones, estado) — keep new code consistent with this rather than mixing English.
- `backend/scrapers/linkedin.py` explicitly documents: always use a secondary LinkedIn account via Playwright, never the primary one.
- Secrets (`GEMINI_API_KEY`, `LINKEDIN_EMAIL/PASSWORD`, `DATABASE_URL`, `RAW_DATA_PATH`) are loaded from `.env` via `python-dotenv`.
