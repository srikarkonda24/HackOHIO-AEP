# GridAware: Network impact engine starter

This starter is derived from the format of the AEP HackOHI/O 2026 `matched_upstream.txt` and `Customer_Clip` shapefile. It creates a **SQLite dependency index** that can answer "Which premises depend on device X?" and "Which devices are upstream of premise Y?".

## Input files
Place these in a local folder `data/` (do NOT push AEP raw data to public GitHub):
- `matched_upstream.txt` (extract from `matched_upstream.zip`)
- `Customer_Clip.shp`, `.shx`, `.dbf`, `.prj`, `.cpg` (extract from `Data1.zip`)

## Installation
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\activate
pip install pyshp fastapi uvicorn
```

## Build once
```bash
python build_index.py --upstream data/matched_upstream.txt --customers data/Customer_Clip.shp --out network.db
```

## Start API
```bash
uvicorn api:app --reload
```

Open http://127.0.0.1:8000/docs and try `GET /devices/search?q=...` to find a device key, then `GET /devices/impact?device_key=...`.

## Notes
- `device_key` is `source_type*source_id` from an upstream token. The full token is `source_type*source_id*device_type*location_id`.
- GIS device layers can be joined later on `location_n` (shapefile-truncated field) and the token's `location_id`.
- A mapped damage location/line/pole does **not** guarantee a direct device match, or that an outage occurred.
- This first version indexes upstream membership but not chronological order of every hop, dynamic switching or phase state. Do not describe it as a complete electrical connectivity simulator.
- `/devices/impact` returns only the first `limit` points for map performance, while the count covers the complete device dependency list.
- `network.db` contains potentially sensitive/sanitized premise mapping; follow competition data-use rules and avoid uploading it to public repositories.
