# GridAware default study area

The Operations Dashboard defaults to a **single verified feeder circuit** near Roanoke, VA so judges see a readable network instead of the full AEP clip. The underlying `gis.db` and `network.db` files are unchanged; filtering is applied at query/render time.

## Candidate comparison (from `scripts/analyze_study_areas.py`)

Roanoke search bbox: approximately `-80.05, 37.05, -79.55, 37.45` (WGS84).

| Circuit ID | Primary segments | Reclosers | Topology-matched equipment | Premises in `network.db` | Demo recloser circuit? | Notes |
|------------|-----------------:|----------:|---------------------------:|-------------------------:|:----------------------:|-------|
| **0000005** | 905 | 30 | 2,232 | 3,527 | **Yes** — all 2,811 demo dependency premises |
| 0000114 | 1,938 | 13 | 1,055 | 1,890 | No | More line mileage, fewer reclosers, no demo tie-in |
| 0000060 | 2,044 | 15 | 847 | 1,233 | No | Larger geographic span, fewer premises |

### Selected: **circuit `0000005`**

- **Demo alignment:** `eo_isolating_eqpt_inst*321305938` → **2,811** dependent premises; every indexed premise uses `premises.circuit_id = 0000005`.
- **Interactive density:** 905 primary segments and 30 reclosers with strong `location_n` ↔ `devices.location_id` joins.
- **ARCOS damage:** GIS `Circuit` values (e.g. `CIR27`) do **not** match `circuit_id`. Damage in the study view uses a **geographic bbox** around circuit geometry (~598 points in bounds at last analysis). Enable the damage layer to see them.

## Filtering behavior

| Layer group | Filter method |
|-------------|----------------|
| Primary, reclosers, switches, fuses, transformers | `circuit_id` or `aep_circui` in feature properties (`GET /gis/features?circuit=0000005`) |
| Historical damage | Geographic bbox from `bounds_wgs84` in study config (documented exception) |
| Modeled customer exposure | **No geographic cap** — full dependency set from `/scenarios/device-unavailable`; map `fitBounds` includes all returned coordinates |

## Regenerating counts

```bash
python scripts/build_gis_layers.py   # if GIS DB missing
python scripts/analyze_study_areas.py  # writes data/processed/study_area.json
```

Committed fallback: `config/study_area.json` (API loads processed copy first when present).

## Limitations

- Circuit IDs in GIS are only as accurate as the source shapefile attributes; filtering does not prove electrical connectivity.
- Premises or dependencies outside `0000005` may still appear in scenario results if the upstream index says so; the map zooms to the full result set.
- Disabling “Study circuit filter” in the UI returns to viewport/bbox loading for dense layers (full territory still on disk).
