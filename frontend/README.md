# BHUSURAKSHA AI — Frontend

React + Vite dashboard for the landslide early warning and risk monitoring
platform. Talks to the FastAPI backend in [`../backend`](../backend) — it
renders only data the API actually returns, with explicit loading, error,
and empty states (never a blank page or invented numbers).

## Install

```bash
npm install
```

## Configure

Copy the example env file and adjust if your backend runs somewhere other
than the default:

```bash
cp .env.example .env
```

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Run

Make sure the backend is running first (see [`../backend/README.md`](../backend/README.md)):

```bash
cd backend
uvicorn app.main:app --reload
```

Then, in a separate terminal:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

If the backend is unreachable, the sidebar shows "Backend Offline" and each
page shows a retry-able error state instead of blank/fake content.

## Pages

| Route             | Page            | Backend calls                                                    |
| ------------------ | --------------- | ----------------------------------------------------------------- |
| `/`                 | Dashboard        | `GET /zones`, `GET /alerts`, `GET /india/summary`, `GET /data-status` |
| `/risk-map`         | Risk Map         | `GET /zones`, `GET /alerts`, `GET /zones/{id}`, `GET /landslides/map`, `GET /landslides/{id}`, `GET /data-sources` |
| `/alerts`           | Alert Center     | `GET /alerts?status=active\|resolved`, `GET /zones`               |
| `/analytics`        | Analytics        | `GET /zones`, `GET /zones/{id}`, `GET /data-status`, `GET /landslides` |
| `/risk-analysis`    | Risk Analysis    | `GET /zones`, `GET /zones/{id}`, `POST /predict-risk`             |
| `/data-sources`     | Data Sources     | `GET /data-status`, `GET /data-sources`, `GET /data-sources/{id}` |
| `/data-status`      | System Status    | `GET /health`, `GET /data-status`                                 |

Navigation is grouped in the sidebar: **Overview** (Dashboard, Risk Map,
Alerts), **Intelligence** (Analytics, Risk Analysis), **Data** (Data
Sources, System Status). The sidebar is collapsible on desktop and becomes
a slide-out drawer on mobile.

Every page except Dashboard is route-level code-split (`React.lazy` +
`Suspense`, with a skeleton fallback — never a blank screen while a chunk
loads); a `PageErrorBoundary` around the routes means a rendering error in
one page can't take down the sidebar/topbar, and an unmatched route shows
a plain 404 page rather than a blank one.

Risk Analysis is a dedicated risk-explanation page: pick any monitored
zone and see its live `POST /predict-risk` result broken into a rule-based
**Risk Factors** bar chart (specific to that zone's current inputs) and,
only when the ML model produced the prediction, a separately labeled
**Model-Level Feature Importance** chart — the RandomForest's global
`feature_importances_`, explicitly never presented as an explanation of
that one prediction.

`Risk Map` is an interactive Leaflet/OpenStreetMap view — no API key
required. Markers use each zone's real `latitude`/`longitude` from
`GET /zones`, colored and sized by `risk_level`; the map auto-fits to
whichever zones are currently visible (all, or filtered to one risk
level) rather than a fixed hardcoded center. Clicking a marker or a zone
in the side list opens a popup with a "View Details" button that fetches
`GET /zones/{id}` for the full environmental/risk-factor breakdown. A zone
with an active alert (matched only via the backend's own `zone_id`, never
guessed) is flagged in both the popup and the list.

Risk Map's **Historical Landslides** layer queries `GET /landslides/map`
(bounded to the current map viewport, re-queried on pan/zoom — never the
whole table) and renders clustered markers (`leaflet.markercluster`) as
neutral slate diamonds, deliberately not risk-colored or circular so a
past event is never mistaken for a current risk marker. Supports state,
data-source, and date-range filters; clicking an event opens a detail
modal (event date, state, district, type, severity, source dataset,
coordinates — a field the source dataset didn't provide reads "Not
available", never "Unknown"). With zero real events registered, the
layer honestly shows "No historical landslide data available" instead of
a fake or missing layer.

Zone details (opened from the Risk Map or Alerts) also show a **Live
Weather** section (temperature, humidity, rainfall, last observation, data
source, or "Live weather currently unavailable.") with a manual refresh
button, plus a **Weather History** section with small charts once at least
two observations exist. The Dashboard's "Refresh Environmental Data" button
calls `POST /weather/refresh-all` and reports zones updated / risk updates
/ alerts generated / weather unavailable — current weather is one input
signal, not a validated forecast (see `backend/docs/WEATHER_LIMITATIONS.md`).

The Dashboard's **India Monitoring Overview** and the Data Status page's
**Pan-India Monitoring Architecture** card both call `GET /india/summary`
/ the `india_monitoring` field of `GET /data-status` to show real counts
(monitoring regions, real-data regions, demo regions, historical landslide
events) with a coverage-status badge — this is data coverage reporting,
never a claim that landslide risk is monitored everywhere in India.

The **Data Sources** page lists 5 category cards (landslide, rainfall,
DEM, land cover, boundaries — each "Available"/"Not Configured" from
`GET /data-status`'s `real_data` block) and a **Registered Data Sources**
list (`GET /data-sources`); clicking one opens a detail modal
(`GET /data-sources/{id}`) with provider, license, coverage, checksum, and
processing status, plus (for `historical_landslide` sources) a **Data
Completeness** section from `GET /data-sources/{id}/quality` — how much
of the schema the source's stored records actually populated
(coordinates/date/state/district/type/severity), explicitly labeled
completeness, never scientific or prediction accuracy. Ingestion itself
is CLI-only (`scripts/ingest_dataset.py`) — this page is read-only, never
an upload form.

**System Status** reports Backend / Database / PostGIS / ML Model / Live
Weather / Real Data Sources, each as Operational / Degraded / Not
Configured / Unavailable — a service is only ever marked Operational once
`GET /health` or `GET /data-status` actually confirms it, never assumed.

## Structure

```text
src/
├── components/
│   ├── layout/     AppShell, Sidebar (grouped, collapsible), Topbar, PageErrorBoundary, RouteFallback
│   ├── ui/         StatusBadge, EmptyState, LoadingState, ErrorState
│   ├── risk/       RiskScore, RiskFactors
│   ├── data/       DataSourceCard
│   ├── charts/     RiskDistributionChart (lazy-loaded out of Dashboard's eager bundle)
│   ├── map/        RiskMapContainer, RiskMarker, ZonePopup, MapLegend, MapControls, MapLayers,
│   │               HistoricalEventsLayer, MapViewportWatcher, mapIcons
│   └── StatCard, RiskBadge, AlertCard, ZoneDetailModal, EventDetailModal
├── pages/          Dashboard, RiskMap, Alerts, Analytics, RiskIntelligence, DataSources, DataStatus, NotFound
├── services/       api.js — axios client + one function per backend endpoint
├── hooks/          useApi.js — loading/error/data fetch hook + backend health polling
└── utils/          riskUtils.js — risk sorting, badge/chart colors, formatting
```
