# GridAware restoration model (Level 4)

## Network (`illustrative_network_v2.json`)

Radial fictional graph — **not** AEP GIS.

```
SRC —A— N_MAIN — N_BUS —S1— B — HOSPITAL
                  |                ^
                  D — N_TRUNK —S2— (tie, illustrative)
                    ├— C — RES1
                    ├— E — FIRE
                    └— F/G — RES2 / RES3
```

- **7 repairable components:** A (pole), B (hospital wire), C (xfmr), D (trunk wire), E (fire switch), F (xfmr), G (lateral).
- **5 customer groups:** Hospital, Fire, three residential zones.
- **S1:** sectionalizer on hospital branch (starts **closed**).
- **S2:** illustrative hospital **tie** (starts **open**; scenario-only, not real AEP backfeed).

### Switch semantics

| Action | Effect |
|--------|--------|
| **OPEN S1** | De-energizes faulted hospital branch conductor **B** from the bus (after isolating). |
| **CLOSE S2** | Closes tie from energized **trunk** to hospital tap — requires **S1 open**, **A** and **D** intact, **B** may remain damaged. |
| **CLOSE S1** | Normal reclose after **B** repaired. |

Opening a switch **does not** by itself restore customers; only defined topology changes + energized paths do.

BFS from `SRC` respects edge `requires_component`, `requires_switch`, and tie blocking when **S1** is closed.

## Step-restoration showcase

**Damage: B only** (hospital wire).

| Strategy | Hospital restore (typical, 12 workers, 4/crew) |
|----------|-----------------------------------------------|
| Repair-only | ~13.5 h (after **B** repair completes) |
| Step restoration | ~2.0 h (after **CLOSE S2**, with **OPEN S1** + tie in parallel crews) |

Example optimized action sequence:

1. `OPEN_S1` (1.5 h)  
2. `CLOSE_S2` (2.0 h, illustrative tie)  
3. Repair **B** (can follow without holding hospital out)

## Optimization

Exhaustive DFS over interleaved **repair** and **switch** actions (small graph, cap depth 14).

**Objective (simulation policy, not AEP dispatch):**

1. Precedence / safety preconditions  
2. Minimize hospital restore time  
3. Minimize fire restore time  
4. Minimize customer-weighted residential restore  
5. Minimize makespan  

Compare **repair_only_optimized** vs **step_restoration_optimized** on the same damage and crews.

## Labor data (AEP workbook)

**Source:** `Install_Labor_HackOHIO.xlsx` → `python scripts/build_repair_labor_config.py` → `config/restoration/repair_labor_v1.json`

**Formula:** `(Avg Removal + Avg Install person-hours) × 4.5 ILM / workers_per_crew` (ILM from workbook = 4.5)

| Repair type | Workbook block | ARCOS proxy |
|-------------|----------------|-------------|
| Pole | Pole CU Average Hours by Size — **Medium (40–55 ft)** | Damaged Pole |
| Wire | **Service CU Average Hours** | Damaged Wire (approximate; no primary conductor aggregate in sheet) |
| Transformer | Transformer CU — **25 kVA** (47 CUs) | Damaged Equipment |
| Switch | Switch CU Average Hours | Damaged Switch |

## API response audit fields

- `timeline` with repair/switch events, crew times, snapshots  
- `group_restoration_times`, weighted metrics  
- `comparison.hospital_restore_delta_hours`  
- `labor_config_metadata`, `limitations`

## Limitations

- Illustrative tie **S2** is a labeled scenario assumption.  
- No switching study, safety clearance, or confirmed AEP operating procedure.  
- Customer counts are hypothetical aggregates for weighting only.
