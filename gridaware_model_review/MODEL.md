# GridAware Stage 4 revised model — measured weather-damage associations

## Standard method: empirical exposure enrichment (case-time / background comparison)

Define for weather condition C:

E(C,d) = [number of unique (reported date, weather area) pairs with damage type d AND C / number of unique pairs containing damage type d] / [number of area-days with C / total area-days].

This is a **descriptive association ratio**, not the probability of equipment damage or a power outage. No full outcome population or negative labels were supplied.

For any date with a report, use the maximum gust, summed precipitation, minimum temperature and summed snowfall of that date and previous two dates (because report dates can lag damage). The normal-weather comparison uses the same 3-day window and four weather grid points.

Conditions tested: top decile for wind, precipitation, snowfall; below/freezing minimum temperature 32F. Snowfall and precipitation should never be arithmetically added together; snowfall in cm, precipitation in inches of liquid-water equivalent.

Damage types in raw data: Damaged Wire, Damaged Pole, Damaged Switch, Damaged Equipment, Damaged Light. Switch is a report classification, not necessarily a particular physical switch asset.

## Prototype risk model to implement

1. For scenario inputs W,R,T,S compute historical percentile/tail rarity against 3-day weather baselines (or derive a 1-day baseline for 1-day scenario controls; do NOT compare one-day inputs with 3-day thresholds).
2. Use the enrichment table as explanatory *historical evidence only*, and show sample support (unique day-grid pairs). Do not multiply ratios by made-up impact probabilities.
3. Under an optional **assumption-only** layer, wire High; pole/switch/equipment Medium; light Low as user-supplied qualitative interpretations of damage consequence. This is NOT a training label for outage probability.
4. Return a transparent Low/Medium/High *relative outage concern* band based on a documented hazard heuristic. Report evidence quality separately and never output percent outage probability. Do not claim network memberships establish failure likelihood.

## Limitations

- Only 55 distinct damage report dates; the February 2025 cluster contributes a disproportionate share. Per-type pairs overlap days and are not independent storms.
- Historical ARCOS may be selected/incomplete; days without damage entries are not verified negatives.
- ERA5 modeled gridded estimates at four representative points; not fault-site measurements.
- Date is reporting date, not confirmed weather-related occurrence time. 3-day lookback is exploratory and cannot correct uncertain event time completely.
- Seasonal/weather confounding and spatial correlation. The enrichment is not a validated probability.
- No reliable outage status/customer interruption labels, so cannot fit a supervised customer outage probability.

## How to make a probability model eventually

Acquire a full outage log including interruption timestamp, customers affected, device attribution, and weather periods with **verified outage/non-outage coverage**. Then fit a regularized logistic regression P(outage|W,R,T,S,asset exposure) with event-level temporal validation, or a negative-binomial count model if modeling verified damage counts with known reporting coverage.
