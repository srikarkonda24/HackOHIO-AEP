# Storm restoration operational overlays

GridAware’s Level 4 simulator uses **AEP workbook direct person-hours** with a single **4.5 indirect labor multiplier (ILM)** per `repair_labor_v1.json`. Storm controls do **not** change those source values.

## Why baseline ETAs are often “Within 1 day”

With **minor** severity and **normal** access, each repair is roughly **2–4 central hours** with four workers per crew (`(removal + install) × quantity × 4.5 ÷ 4`). Even **seven sequential repairs on one crew** total about **19 hours**; with **12 workers (3 crews)** parallel work often finishes the modeled home (**RES1**) in **under five hours**. The optimizer is not skipping repairs—the math is simply sub‑24‑hour for this small illustrative graph.

## Simulated storm controls

Configured in `config/restoration/storm_operational_assumptions.json`:

| Control | Effect |
|--------|--------|
| **Damage severity** | Multiplies **work quantity** per repair type (e.g. major wire = 2.0 units). Duration uses the existing formula with higher `quantity` only. |
| **Access conditions** | Sets **crew mobilization** and **per‑site access ready** times. Repairs cannot **start** before `mobilization + site_access`; duration once started is unchanged. |
| **Extra mobilization** | Adds simulated staging delay (hours) to mobilization. |

Switching durations and graph connectivity rules are unchanged.

## API

`POST /restoration/simulate` accepts `damage_severity`, `access_conditions`, and `extra_mobilization_hours`. Response includes `storm_context`, `labor_preview`, `modeled_home_restore_hours`, and `all_groups_restore_hours`.
