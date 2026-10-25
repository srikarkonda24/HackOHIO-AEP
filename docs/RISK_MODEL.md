# GridAware Stage 4 — Historical weather relative outage risk

## What this is

A **Low / Medium / High relative outage concern** band for **hypothetical 3-day storm conditions**. It is **not** a verified customer outage probability, live forecast, or restoration estimate.

## Data used

| Source | Role |
|--------|------|
| **AEP ARCOS damage reports** (1,659 reports, 55 distinct report dates) | Historical damage *report* dates and categories |
| **ERA5 via Open-Meteo** (`historical_weather_era5.csv`) | Daily max gust (mph), liquid precip (in), min temp (°F), snowfall (cm→in) at four southwest Virginia sample points |
| **`arcos_weather_join.csv`** | Research join of report dates to nearest sample-point weather |
| **`three_day_weather_damage_enrichment.csv`** | Precomputed enrichment ratios E(C,d) for documented condition thresholds |

February 2025 contributes a large share of reports; distinct date–location pairs (106) are **not** independent storms.

## Storm window (consistent 3-day)

For both historical enrichment and the simulator:

- **Max wind gust** = maximum daily gust over the 3-day window  
- **Total precipitation** = sum of daily liquid equivalent (in)  
- **Minimum temperature** = minimum daily min temp (°F)  
- **Total snowfall** = sum of daily snowfall (converted to inches)

Report dates in the analysis used the report day plus the **previous two days** (damage may be reported after the storm).

## Enrichment formula (descriptive only)

For weather condition C and damage category d:

**E(C,d) = (D_C,d / D_d) / (H_C / H)**

- D_C,d = distinct (report date, weather grid) pairs with category d when C holds  
- D_d = all such pairs for category d  
- H_C = historical area-days with C  
- H = all comparable historical area-days  

Enrichment explains **association with damage reports**, not P(outage). We **do not multiply** enrichments into a single score (weather variables are correlated).

## Damage categories (ARCOS → modeling assumptions)

| ARCOS category | Reports (approx.) | Prototype service-impact assumption |
|----------------|-------------------|-------------------------------------|
| Damaged Wire | 861 | High |
| Damaged Pole | 355 | Medium |
| Damaged Switch | 357 | Medium |
| Damaged Equipment | 81 | Medium |
| Damaged Light | 5 | Low (sparse — never drives HIGH alone) |

These are **assumptions** for narrative context, not training labels.

## Data-derived thresholds (from enrichment / ERA5 3-day windows)

Pooled across four grid points (6,808 windows):

| Input | Enrichment / rule threshold | Notes |
|-------|----------------------------|--------|
| Max wind gust | **≥ 40.5 mph** | Matches pooled 90th percentile |
| Total precipitation | **≥ 0.9465 in** | Matches ~90th percentile |
| Min temperature | **≤ 32 °F** | Freezing condition in enrichment table |
| Snowfall | **> 0 in** (3-day sum) | “Any snow” condition |

Percentiles also used: p25/p50/p75/p95 for calm guard, moderate tiers, and wind floor (see JSON).

## Classification rule (`historical_weather_informed_v1`)

Implemented in [`historical_weather_risk.py`](../gridaware_network_starter/historical_weather_risk.py). Constants in [`config/risk_model/historical_weather_risk_model.json`](../config/risk_model/historical_weather_risk_model.json) (regenerate with [`scripts/build_risk_model_params.py`](../scripts/build_risk_model_params.py)).

1. **Calm guard → LOW** if wind &lt; p25, precip &lt; p25, snow = 0, temp &gt; 32 °F.  
2. Else **hazard score**: severe wind +3, moderate wind (≥ p75) +1; severe precip +2, moderate precip (≥ p50) +1; freezing +1; snow +2 if also freezing or moderate wind else +1.  
3. **Band**: score ≤ 1 → LOW; 2–4 → MEDIUM; ≥ 5 → HIGH.  
4. **Wind monotonicity floor**: wind ≥ 40.5 → at least MEDIUM; wind ≥ p95 (44.7 mph pooled) → at least HIGH.  
5. **Response** includes enrichment rows for active conditions and separate `damage_impact_assumptions_context` — assumptions are **not** numerically folded into the score.

## Evidence quality

- Narratives flag associations with **&lt; 10** matched date–location pairs as sparse.  
- **Damaged Light** (4 pairs in enrichment) is excluded from driving high concern via small-sample artifacts.

## Geographic scope

Assessments use the nearest of four ERA5 sample points to the premise coordinates, within the documented southwest Virginia study footprint. Premises outside that coarse coverage should not be extrapolated.

## What we do not claim

- Confirmed customer outages from ARCOS or topology  
- Live grid status or exact feeder paths  
- Outage percentages or ETR (Stage 5+)  
- That underground service type implies an all-underground supply path
