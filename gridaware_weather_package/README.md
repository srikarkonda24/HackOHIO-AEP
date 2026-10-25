# GridAware historical weather + AEP ARCOS research package

**What is already real:** `aep_arcos_damage_events.csv` is extracted from the supplied AEP ARCOS shapefile; `aep_event_summary.json` summarizes its dates. Coordinates are the supplied damage report positions, not necessarily fault locations.

**What still needs downloading:** The Open-Meteo ERA5 dataset. This environment could not connect to the API, so no weather readings have been invented or shipped.

## Run once on the user's own Windows PC (with Internet)

```powershell
pip install requests pandas
python build_weather_dataset.py
```

The script downloads Open-Meteo ERA5 daily weather for 2022-01-01 to 2026-08-31 at 4 coarse representative locations in the AEP southwest Virginia footprint. It outputs:

- `historical_weather_era5.csv` (all observed daily values by weather point)
- `arcos_weather_join.csv` (ARCOS report *dates* joined to same-day weather at nearest sampled point)
- `weather_sources.json` (API URLs and exact units/model provenance)

Four inputs are maximum gust (mph), precipitation (inches liquid water equivalent including snow), minimum temp (°F), snowfall (cm). Convert snowfall to inches by dividing cm by 2.54 for UI. ERA5 is gridded reanalysis; readings are estimates, not direct readings at each damaged asset. A point nearest-center coarse join is a convenience, not a validated spatial fit; use precise spatial matching if spatial variations matter. Different stations / ERA5 grid cells can have different values.

**Statistical caveat:** Historical selected damage reports include many reports for one event; they are NOT independent damage outcomes. Missing ARCOS records are NOT verified no-damage days. Group by independent storm episode for evaluations. Enrichment is descriptive: E(C)=(damage-report dates matching weather C / total damage-report dates) / (historical weather dates matching C / total historical dates). It is not P(outage | C) or calibrated customer-specific outage probability. If no enough independent events support C, return `insufficient_evidence` rather than High/Medium/Low based on that ratio alone. The formula only applies to clearly predeclared weather event conditions, not arbitrary sliding four-dimensional lookup with near-empty counts. Do not treat min temp+precip as confirmed ice.

License/attribution: Open-Meteo Historical Weather API, https://open-meteo.com/en/docs/historical-weather-api ; ERA5 ECMWF/Copernicus provenance should be preserved. Review Open-Meteo usage terms before distribution. No network call at app runtime; run script during training only.
