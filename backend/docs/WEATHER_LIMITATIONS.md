# Live weather — scientific limitations

Phase 6 adds a live weather integration (`app/services/weather_service.py`)
that fetches current temperature, humidity, and a real 24-hour rainfall sum
(computed from the provider's hourly precipitation series, not a fabricated
single value) for a zone's coordinates via
[Open-Meteo](https://open-meteo.com) — a free public API, no key required.

**This does not turn BHUSURAKSHA AI into a validated landslide early-warning
system.** Current weather conditions are only one input signal. A
scientifically defensible landslide forecast would also need, at minimum:

- **Multi-day/multi-week rainfall accumulation and intensity**, not just a
  24-hour snapshot — landslides are frequently triggered by cumulative
  soil saturation, not a single reading.
- **Soil moisture and geotechnical/geology data** (soil type, permeability,
  prior saturation) — not available from a weather API.
- **Validated terrain data**: slope, elevation, and aspect from a real DEM
  (Phase 3's `geospatial/` pipeline is the intended path for this, once a
  real DEM source is supplied — see [DATA_SOURCES.md](DATA_SOURCES.md)).
- **Vegetation / land cover** data reflecting actual current conditions,
  not the seeded demo value.
- **A validated historical landslide inventory** to correlate conditions
  against actual past events — the ML model in `ml/` is trained on
  synthetic demo data, not real landslide outcomes.

What live weather integration *does* provide: a real, current environmental
reading that can refresh a zone's `temperature`, `humidity`, and
`rainfall_24h` fields and feed them through the same risk engine (ML or
rule-based fallback) already used elsewhere in the app — improving
situational awareness without pretending to be more than it is.

If the weather provider is unavailable, previously stored zone values are
left untouched (see `_apply_weather_to_zone` in `app/routes/weather.py`)
rather than being zeroed or nulled out.
