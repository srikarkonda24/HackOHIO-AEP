# GridAware — Development Roadmap

Living progress tracker for HackOHI/O 2026. **Planned items are not implemented** unless listed under [Completed](#completed-work).

---

## Completed work

- [x] Process AEP **customer GIS** (`Customer_Clip` shapefile) and **upstream topology** (`matched_upstream.txt`) into SQLite via [`build_index.py`](gridaware_network_starter/build_index.py).
- [x] Schema: `premises`, `devices`, `dependencies` with indexes for device and premise lookups.
- [x] **FastAPI** read-only network-impact API ([`api.py`](gridaware_network_starter/api.py)): `/health`, `/devices/search`, `/devices/impact`, `/premises/{premise_id}/upstream`.
- [x] Local verification of device search and impact queries (Swagger `/docs` and manual calls).
- [x] Example device **`eo_isolating_eqpt_inst*321305938`**: **2,811** potentially dependent premises (full count via `/devices/impact`; use `limit` up to 5000 to return all customer points for mapping).
- [x] Repository architecture and roadmap documentation ([`ARCHITECTURE.md`](ARCHITECTURE.md), this file).
- [x] **Operations Dashboard (M1)** — Next.js app in [`frontend/`](frontend/): dark layout, equipment search, impact summary cards, MapLibre map with clustering, demo device on load, Next.js rewrite proxy to FastAPI.
- [x] **GIS infrastructure (M2)** — organized `data/raw/` ZIPs; [`scripts/build_gis_layers.py`](scripts/build_gis_layers.py) writes `data/processed/gis.db`; FastAPI `/gis/*`; toggleable MapLibre layers; click-to-inspect; exact `location_n` ↔ `location_id` join for dependent-premise lookup.
- [x] **M3A — Interactive equipment failure / customer exposure scenarios** — GIS asset select with validated topology match; **Simulate device unavailable** in inspect panel; `/scenarios/device-unavailable` (+ `/summary`) returns the **full** dependency premise set (no 5,000 map cap); fuchsia map layer for **modeled potential exposure**; scenario summary panel and **Clear scenario**; default layers: primary lines, reclosers, ARCOS damage on; dense layers off until toggled; pytest regression for demo recloser **2,811** premises ([`tests/test_scenarios.py`](gridaware_network_starter/tests/test_scenarios.py)).
- [x] **Focused study area (Roanoke demo)** — Default Operations map to **circuit `0000005`** (905 primary segments, 30 reclosers, demo recloser **2,811** dependency premises); circuit filter on `/gis/features?circuit=`; damage via geographic bbox; full dataset retained; see [`docs/STUDY_AREA.md`](docs/STUDY_AREA.md) and [`config/study_area.json`](config/study_area.json).
- [x] **Customer network context engine (Stage 2)** — `GET /customers/{premise_id}/network-context`; evidence-typed joins (`recorded_location_reference`, `upstream_index_membership`, `gis_attribute_reference`); circuit conflict reporting; tests on premise `000052580` ([`network_context_service.py`](gridaware_network_starter/network_context_service.py)).
- [x] **Customer-facing dashboard foundation (Stage 3)** — Next.js `/customer` route; premise ID entry with verified example `000052580`; plain-English sections wired to network-context API; technical details/limitations collapsible; loading, 404, and partial-data states; Vitest on summary helpers; Operations map unchanged at `/`.
- [x] **Historical weather relative outage risk (Stage 4)** — Documented enrichment + hazard classifier; `POST /customers/{premise_id}/risk-assessment`; model JSON from ERA5 + enrichment CSV; customer **Storm Outage Risk Simulator** with presets calling live API; [`docs/RISK_MODEL.md`](docs/RISK_MODEL.md).
- [x] **Restoration simulation foundation (Stage 5A)** — Illustrative radial network; AEP labor config + duration formula; BFS outage logic; crew scheduler with baseline vs optimized; `/restoration/*` API; `/prediction` + `/restoration` navigation; [`docs/RESTORATION_MODEL.md`](docs/RESTORATION_MODEL.md).
- [x] **Step restoration & isolation (Level 4)** — v2 graph (7 components, 2 switches, 5 groups); switch-aware BFS; repair + switching action optimizer; repair-only vs step-restoration comparison; auditable timelines; UI labor provenance warning.
- [x] **End-to-end simulation vertical slice** — Verified membership groups ([`electrical_model.py`](gridaware_network_starter/electrical_model.py)); unified [`POST /simulation/scenario`](gridaware_network_starter/simulation_api.py) (multi-failure exposure, rule-based risk, labor estimates, 2-crew optimizer, dependency restoration, alerts, template concierge); operator **logical dependency diagram** UI ([`GridAwareDashboard.tsx`](frontend/components/dashboard/GridAwareDashboard.tsx)); docs [`ELECTRICAL_MODEL.md`](docs/ELECTRICAL_MODEL.md), [`MODEL_ASSUMPTIONS.md`](docs/MODEL_ASSUMPTIONS.md), [`DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

### M1 limitations (known)

- `/devices/impact` returns at most **5,000** customer points per request (use scenario endpoints for full-map exposure).
- Requires FastAPI running locally (`127.0.0.1:8000`); proxy URL configurable via `BACKEND_URL`.

### M2 limitations (known)

- Dense layers (primary, secondary, poles, transformers) load **by map bbox**, not the full clip, and appear only above their `min_zoom`.
- Secondary lines and emergency facilities are **off by default** in the UI (`DEFAULT_LAYER_VISIBILITY`).
- ARCOS damage has **no** `location_n`; it cannot be joined to `network.db` without a later probabilistic matcher.
- Emergency facilities are USGS points (Web Mercator), not AEP equipment.
- Multiple GIS assets can share one `location_n` (pole + recloser + line end). The UI lists all exact device matches rather than guessing which object is electrically “the” device.
- `network.db` was not modified. Join stats are read-only.

### Study area limitations (known)

- Default UI filters GIS **infrastructure** by shapefile `circuit_id` / `aep_circui`; **ARCOS damage** uses a **geographic bbox** because ARCOS `Circuit` labels (e.g. `CIR27`) do not match `circuit_id`.
- Scenario impact counts and customer coordinates are **never** clipped to the study area; the map zooms to the full API result.
- Uncheck **Limit map to study circuit** to load layers by map viewport against the full clip (bbox rules apply).

### M3A limitations (known)

- **Single unavailable device** per active scenario (state shaped for future multi-device union).
- No switching study, isolation logic, confirmed outage boundaries, or restoration / ETR estimates.
- Scenario exposure equals **upstream dependency membership** for the selected device only.
- Damage and emergency map layers cannot trigger topology-validated simulate actions.

---

## Current milestone

**M3 — ARCOS damage matching (beyond display)**

- [ ] Optional probabilistic link from damage points to nearby/related equipment, with explicit confidence.
- [ ] Keep ARCOS labeled as historical work records, not outage ground truth.

**Exit criteria for M3A:** Met — operators can select GIS equipment with an exact topology join, run a labeled device-unavailable scenario with correct full premise counts, see modeled exposure on the map distinct from baseline impact view, and clear the simulation.

---

## Planned work (future milestones)

### M3 — ARCOS damage matching

- [ ] Load and normalize ARCOS (or provided damage) records. **Points are already on the map.**
- [ ] Match to equipment/locations with explicit confidence—not as outage ground truth.
- [ ] Operations UI: match review beyond identifier-only joins.

### M3B — Multi-device scenarios (follow-on)

- [ ] Multiple unavailable devices with customer-set union/deduplication on the same scenario model.
- [ ] Shared scenario API types for crew/labor modules (M4+).

### M4 — Repair labor and duration

- [x] **Prototype (Stage 5A)** — Workbook extraction script; ILM 4.5; crew duration formula; ±10% ETA band on labor.
- [ ] Full material/CNC/access adders from all workbook sheets.

### M5 — Dependency-aware restoration scheduling

- [x] **Prototype (Stage 5A)** — Illustrative graph, exhaustive order search, critical-facility lexicographic objective.
- [ ] Step restoration tied to real `network.db` topology; versioned plan artifact for customer ETR (Stage 5B+).

### M6 — Outage risk bands

- [x] **Prototype relative bands (Stage 4)** — Historical ERA5 + ARCOS enrichment; LOW/MEDIUM/HIGH via documented hazard rule; customer API + UI; not calibrated probabilities.
- [ ] Operations map overlays and richer evidence review.

### M7 — Customer Concierge and alerts

- [ ] Premise-centric UI: risk, prep guidance, ETR **from published operations plan**.
- [ ] Alert eligibility and notification workflows (policy-driven).
- [ ] Tie ETR updates to plan version changes (see [ARCHITECTURE.md](ARCHITECTURE.md)).

### M8 — Responsible AI and demo hardening

- [ ] Grounded explanations over structured API responses only.
- [ ] Evaluation scenarios for judges (clear verified vs simulated labels).
- [ ] Error handling, observability, and security review for demo deployment.

---

## Optional stretch features

- [ ] Historical outage / ARCOS timeline animation on the map.
- [ ] What-if switching or isolation **simulation** (explicitly labeled, not real-time EMS).
- [ ] Mobile-friendly customer concierge PWA.
- [ ] Multi-utility configuration layer (out of scope for AEP demo unless time permits).
- [ ] Real-time SCADA or AMI integration (almost certainly out of scope; simulation only if attempted).

---

## Explicitly out of scope (unless requirements change)

- Rewriting the working SQLite index or breaking existing API contracts without migration notes.
- Committing `network.db` or raw AEP files to public git.
- Claiming confirmed outages from dependency or ARCOS data alone.
- Treating geographic proximity as electrical connectivity.

---

## How to update this file

When a milestone ships, move bullets to **Completed work** with dates optional. Keep **Current milestone** to a single focus. Agent sessions should read [`ARCHITECTURE.md`](ARCHITECTURE.md) for contracts and this file for status.
