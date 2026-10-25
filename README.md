# GridAware (HackOHI/O 2026 — AEP)

AI Outage Concierge: shared backend for an **AEP Operations Dashboard** and **Customer Concierge**, built on AEP topology and customer GIS.

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, schema, API contracts, data semantics, planned modules |
| [ROADMAP.md](ROADMAP.md) | Completed work, current milestone, future plans |

## Repository layout

- [`gridaware_network_starter/`](gridaware_network_starter/) — SQLite index build, `network.db`, FastAPI API (**setup instructions live here**)
- [`frontend/`](frontend/) — Next.js **Operations Dashboard** (MapLibre map, equipment search, GIS layers)
- [`scripts/build_gis_layers.py`](scripts/build_gis_layers.py) — AEP shapefile → `data/processed/gis.db`
- `data/raw/` — original AEP ZIPs (gitignored)
- `data/processed/` — derived GIS database (gitignored)

## Quick start (backend)

From [`gridaware_network_starter/README.md`](gridaware_network_starter/README.md):

1. Place competition data in `gridaware_network_starter/data/` (not committed to git).
2. `pip install pyshp fastapi uvicorn`
3. `python build_index.py --upstream data/matched_upstream.txt --customers data/Customer_Clip.shp --out network.db`
4. `python -m uvicorn api:app --reload` → http://127.0.0.1:8000/docs

Do not upload `network.db` or raw AEP datasets to public repositories.

## Quick start (operations dashboard)

With the API running (above), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — requests go to FastAPI via `/api/backend/*` (default `http://127.0.0.1:8000`). Override with `BACKEND_URL` if needed.

## GIS infrastructure layers

After placing `Data1.zip` and `Data2.zip` in `data/raw/`:

```bash
python -c "import zipfile; from pathlib import Path; raw=Path('data/raw'); dest=raw/'shapefiles'; dest.mkdir(exist_ok=True);
[zipfile.ZipFile(z).extractall(dest/z.stem) for z in raw.glob('*.zip')]"
python scripts/build_gis_layers.py
```

Then restart FastAPI so `/gis/catalog` and `/gis/features` can read `data/processed/gis.db`.

## Demo device (verified)

- **Device key:** `eo_isolating_eqpt_inst*321305938`
- **Potentially dependent premises:** 2,811 (use `/devices/impact?device_key=...&limit=5000` for all map points)
