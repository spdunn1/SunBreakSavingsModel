# SunBreak Dashboard

Agricultural irrigation energy optimization dashboard — FastAPI + vanilla JS.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000

## Architecture

- `main.py` — FastAPI app, API routes
- `simulator/` — 8760-hour bill calculator (core.py + runner.py)
- `load_synth/` — Crop ET engine, irrigation system models
- `scheduler/` — Baseline + TOU-optimized pump scheduler
- `solar/` — Synthetic PV generation profiles
- `tariffs/` — PG&E / SCE / SDG&E rate schedules (2026)
- `templates/index.html` — Single-page dashboard
