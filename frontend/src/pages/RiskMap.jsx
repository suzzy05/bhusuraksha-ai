import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import EventDetailModal from "../components/EventDetailModal"
import RainfallObservationDetailModal from "../components/RainfallObservationDetailModal"
import ErrorState from "../components/ui/ErrorState"
import Loading from "../components/ui/LoadingState"
import RiskBadge from "../components/RiskBadge"
import ZoneDetailModal from "../components/ZoneDetailModal"
import MapControls from "../components/map/MapControls"
import MapLayers from "../components/map/MapLayers"
import MapLegend from "../components/map/MapLegend"
import RiskMapContainer from "../components/map/RiskMapContainer"
import TimelineControl from "../components/map/TimelineControl"
import { useApi } from "../hooks/useApi"
import { getAlerts, getDataSources, getLandslidesInBbox, getRainfallInBbox, getZones } from "../services/api"
import { sortByRisk } from "../utils/riskUtils"

export default function RiskMap() {
  const zonesState = useApi(getZones, [])
  const alertsState = useApi(getAlerts, [])
  const [searchParams, setSearchParams] = useSearchParams()

  const [filter, setFilter] = useState("ALL")
  const [search, setSearch] = useState("")
  const [stateFilter, setStateFilter] = useState("ALL")
  const [alertsOnly, setAlertsOnly] = useState(false)
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [detailZoneId, setDetailZoneId] = useState(null)
  const [detailEventId, setDetailEventId] = useState(null)
  const [detailRainfallId, setDetailRainfallId] = useState(null)
  const [fitToken, setFitToken] = useState(0)
  const [panelOpen, setPanelOpen] = useState(false)
  const [layersOpen, setLayersOpen] = useState(false)
  const [activeLayers, setActiveLayers] = useState(() => new Set(["risk_zones", "alerts"]))

  const [mapBounds, setMapBounds] = useState(null)
  const [eventState, setEventState] = useState("ALL")
  const [eventSourceId, setEventSourceId] = useState("ALL")
  const [eventStartDate, setEventStartDate] = useState("")
  const [eventEndDate, setEventEndDate] = useState("")

  const [animationStepIndex, setAnimationStepIndex] = useState(0)
  const [animationStepCount, setAnimationStepCount] = useState(0)
  const [animationPlaying, setAnimationPlaying] = useState(false)
  const [animationSpeedMs, setAnimationSpeedMs] = useState(250)

  const zones = zonesState.data || []
  const alerts = alertsState.data || []
  const historicalLayerOn = activeLayers.has("historical_landslides")
  const eventAnimationOn = activeLayers.has("event_animation")
  const rainfallLayerOn = activeLayers.has("rainfall")

  const alertsByZoneId = useMemo(() => {
    const map = new Map()
    for (const alert of alerts) {
      // Only ever associate an alert with a zone the backend itself linked
      // via zone_id — never inferred or guessed.
      if (alert.zone_id != null && !map.has(alert.zone_id)) map.set(alert.zone_id, alert)
    }
    return map
  }, [alerts])

  const stateOptions = useMemo(
    () => [...new Set(zones.map((zone) => zone.state))].sort(),
    [zones],
  )

  // "View on Map" from Alert Center arrives as ?zone=<id> — select and open
  // detail once zones have loaded, then drop the param so it doesn't stick.
  useEffect(() => {
    const zoneParam = searchParams.get("zone")
    if (zoneParam && zones.length > 0) {
      const id = Number(zoneParam)
      if (zones.some((zone) => zone.id === id)) {
        setSelectedZoneId(id)
        setDetailZoneId(id)
      }
      const next = new URLSearchParams(searchParams)
      next.delete("zone")
      setSearchParams(next, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zones])

  const sortedZones = useMemo(() => sortByRisk(zones), [zones])
  const visibleZones = useMemo(() => {
    const query = search.trim().toLowerCase()
    return sortedZones.filter((zone) => {
      if (filter !== "ALL" && zone.risk_level !== filter) return false
      if (stateFilter !== "ALL" && zone.state !== stateFilter) return false
      if (alertsOnly && !alertsByZoneId.has(zone.id)) return false
      if (query && !`${zone.name} ${zone.state}`.toLowerCase().includes(query)) return false
      return true
    })
  }, [sortedZones, filter, stateFilter, alertsOnly, search, alertsByZoneId])

  // The animation layer is a different rendering of the same historical
  // data, not a separate dataset — turning it on implies the same
  // fetch/filter behavior as the static Historical Landslides layer.
  const showHistoricalData = historicalLayerOn || eventAnimationOn

  // A registered-sources dropdown for the historical-event filter — only
  // fetched once the layer is actually turned on.
  const eventSourcesState = useApi(
    () => (showHistoricalData ? getDataSources({ category: "historical_landslide" }) : Promise.resolve(null)),
    [showHistoricalData],
  )

  const boundsKey = mapBounds
    ? [mapBounds.getSouth(), mapBounds.getWest(), mapBounds.getNorth(), mapBounds.getEast()]
        .map((n) => n.toFixed(3))
        .join(",")
    : null

  const historicalEventsState = useApi(
    () => {
      if (!showHistoricalData || !mapBounds) return Promise.resolve(null)
      return getLandslidesInBbox({
        min_lat: mapBounds.getSouth(),
        min_lon: mapBounds.getWest(),
        max_lat: mapBounds.getNorth(),
        max_lon: mapBounds.getEast(),
        source_id: eventSourceId === "ALL" ? undefined : eventSourceId,
        start_date: eventStartDate || undefined,
        end_date: eventEndDate || undefined,
        limit: 500,
      })
    },
    [showHistoricalData, boundsKey, eventSourceId, eventStartDate, eventEndDate],
  )

  const historicalEvents = useMemo(() => {
    const results = historicalEventsState.data?.results || []
    if (eventState === "ALL") return results
    return results.filter((event) => event.state === eventState)
  }, [historicalEventsState.data, eventState])

  // Reset playback whenever the animation layer is turned on or the
  // underlying (already-filtered) event set changes — restarting cleanly
  // beats silently animating a stale/mismatched set.
  useEffect(() => {
    setAnimationStepIndex(0)
    setAnimationPlaying(false)
  }, [eventAnimationOn, historicalEvents])

  // Playback ticks live on the page alongside the rest of this layer's
  // state, matching the existing page-owns-state convention — the layer
  // component and TimelineControl both just read/write stepIndex.
  useEffect(() => {
    if (!animationPlaying || animationStepCount === 0) return
    const id = setInterval(() => {
      setAnimationStepIndex((i) => {
        if (i + 1 >= animationStepCount) {
          setAnimationPlaying(false)
          return i
        }
        return i + 1
      })
    }, animationSpeedMs)
    return () => clearInterval(id)
  }, [animationPlaying, animationSpeedMs, animationStepCount])

  const animationCurrentDateLabel = useMemo(() => {
    if (animationStepCount === 0) return null
    const dated = historicalEvents
      .filter((e) => e.event_date)
      .map((e) => new Date(e.event_date).getTime())
      .filter((t) => !Number.isNaN(t))
      .sort((a, b) => a - b)
    if (dated.length === 0) return null
    const fraction = animationStepCount > 1 ? animationStepIndex / (animationStepCount - 1) : 0
    const idx = Math.min(dated.length - 1, Math.floor(fraction * dated.length))
    return new Date(dated[idx]).toLocaleDateString()
  }, [historicalEvents, animationStepIndex, animationStepCount])

  const animationDatedEventCount = useMemo(
    () => historicalEvents.filter((e) => e.event_date && !Number.isNaN(new Date(e.event_date).getTime())).length,
    [historicalEvents],
  )
  const animationShownCount =
    animationStepCount > 0
      ? Math.round(((animationStepIndex + 1) / animationStepCount) * animationDatedEventCount)
      : 0

  const rainfallState = useApi(
    () => {
      if (!rainfallLayerOn || !mapBounds) return Promise.resolve(null)
      return getRainfallInBbox({
        min_lat: mapBounds.getSouth(),
        min_lon: mapBounds.getWest(),
        max_lat: mapBounds.getNorth(),
        max_lon: mapBounds.getEast(),
        limit: 500,
      })
    },
    [rainfallLayerOn, boundsKey],
  )
  const rainfallObservations = rainfallState.data?.results || []

  function handleFilterChange(level) {
    setFilter(level)
    setSelectedZoneId(null)
  }

  function handleSelectZone(zoneId) {
    setSelectedZoneId(zoneId)
    setPanelOpen(false)
  }

  function toggleLayer(key) {
    setActiveLayers((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function retry() {
    zonesState.reload()
    alertsState.reload()
  }

  if (zonesState.loading || alertsState.loading) return <Loading label="Loading risk map..." />
  if (zonesState.error || alertsState.error) return <ErrorState onRetry={retry} />

  const showZones = activeLayers.has("risk_zones") ? visibleZones : []
  const showAlerts = activeLayers.has("alerts") ? alertsByZoneId : new Map()
  const eventStateOptions = [...new Set((historicalEventsState.data?.results || []).map((e) => e.state).filter(Boolean))].sort()

  return (
    <div className="space-y-3">
      <MapControls
        activeFilter={filter}
        onFilterChange={handleFilterChange}
        onFitAll={() => setFitToken((token) => token + 1)}
        resultCount={showZones.length}
        search={search}
        onSearchChange={setSearch}
        stateFilter={stateFilter}
        onStateChange={setStateFilter}
        stateOptions={stateOptions}
      />

      <label className="flex w-fit items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400 dark:text-slate-500">
        <input
          type="checkbox"
          checked={alertsOnly}
          onChange={(event) => setAlertsOnly(event.target.checked)}
          className="h-3.5 w-3.5"
        />
        Only zones with active alerts
      </label>

      {showHistoricalData && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-3 py-2">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Historical events:</span>
          <select
            value={eventState}
            onChange={(e) => setEventState(e.target.value)}
            aria-label="Filter historical events by state"
            className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2 py-1 text-xs text-slate-700 dark:text-slate-300"
          >
            <option value="ALL">All States</option>
            {eventStateOptions.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </select>
          <select
            value={eventSourceId}
            onChange={(e) => setEventSourceId(e.target.value)}
            aria-label="Filter historical events by data source"
            className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2 py-1 text-xs text-slate-700 dark:text-slate-300"
          >
            <option value="ALL">All Sources</option>
            {(eventSourcesState.data || []).map((source) => (
              <option key={source.source_id} value={source.source_id}>
                {source.name}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={eventStartDate}
            onChange={(e) => setEventStartDate(e.target.value)}
            aria-label="Historical events on or after this date"
            className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2 py-1 text-xs text-slate-700 dark:text-slate-300"
          />
          <input
            type="date"
            value={eventEndDate}
            onChange={(e) => setEventEndDate(e.target.value)}
            aria-label="Historical events on or before this date"
            className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2 py-1 text-xs text-slate-700 dark:text-slate-300"
          />
          <span className="text-xs text-slate-400 dark:text-slate-500">
            {historicalEventsState.loading ? "Loading…" : `${historicalEvents.length} event(s) in view`}
          </span>
        </div>
      )}

      {eventAnimationOn && (
        <TimelineControl
          stepIndex={animationStepIndex}
          stepCount={animationStepCount}
          playing={animationPlaying}
          speedMs={animationSpeedMs}
          currentDateLabel={animationCurrentDateLabel}
          shownCount={animationShownCount}
          totalCount={animationDatedEventCount}
          onPlayPause={() => setAnimationPlaying((p) => !p)}
          onScrub={(value) => {
            setAnimationPlaying(false)
            setAnimationStepIndex(value)
          }}
          onSpeedChange={setAnimationSpeedMs}
          onReset={() => {
            setAnimationPlaying(false)
            setAnimationStepIndex(0)
          }}
        />
      )}

      {zones.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 dark:border-slate-700 py-16 text-center text-sm text-slate-500 dark:text-slate-400">
          No monitored zones available.
        </div>
      ) : (
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative h-[70vh] min-h-[420px] overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700 lg:flex-1">
            <RiskMapContainer
              zones={showZones}
              alertsByZoneId={showAlerts}
              selectedZoneId={selectedZoneId}
              fitToken={fitToken}
              onViewDetails={setDetailZoneId}
              historicalEvents={showHistoricalData ? historicalEvents : null}
              onViewHistoricalEvent={setDetailEventId}
              eventAnimationOn={eventAnimationOn}
              animationStepIndex={animationStepIndex}
              onAnimationStepCountChange={setAnimationStepCount}
              rainfallObservations={rainfallLayerOn ? rainfallObservations : null}
              onViewRainfallObservation={setDetailRainfallId}
              onBoundsChange={setMapBounds}
            />

            <div className="pointer-events-none absolute bottom-3 left-3 z-[1000]">
              <MapLegend showHistorical={showHistoricalData} showAnimation={eventAnimationOn} showRainfall={rainfallLayerOn} />
            </div>

            <div className="absolute right-3 top-3 z-[1000]">
              <button
                type="button"
                onClick={() => setLayersOpen((open) => !open)}
                aria-expanded={layersOpen}
                className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 shadow-md hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Layers
              </button>
              {layersOpen && (
                <div className="mt-1.5 w-56 rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-2 shadow-lg">
                  <MapLayers activeLayers={activeLayers} onToggle={toggleLayer} />
                </div>
              )}
            </div>

            {showZones.length === 0 && (
              <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center">
                <div className="pointer-events-auto rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-4 py-2 text-sm text-slate-600 dark:text-slate-400 dark:text-slate-500 shadow-md">
                  No zones match this filter.
                </div>
              </div>
            )}

            {showHistoricalData && !historicalEventsState.loading && historicalEvents.length === 0 && (
              <div className="pointer-events-none absolute bottom-3 right-3 z-[1000]">
                <div className="pointer-events-auto rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-3 py-2 text-xs text-slate-600 dark:text-slate-400 dark:text-slate-500 shadow-md">
                  No historical landslide data available.
                </div>
              </div>
            )}

            {rainfallLayerOn && !rainfallState.loading && rainfallObservations.length === 0 && (
              <div className="pointer-events-none absolute bottom-14 right-3 z-[1000]">
                <div className="pointer-events-auto rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-3 py-2 text-xs text-slate-600 dark:text-slate-400 dark:text-slate-500 shadow-md">
                  No rainfall observations available in this view.
                </div>
              </div>
            )}
          </div>

          <ZoneListPanel
            zones={showZones}
            alertsByZoneId={showAlerts}
            selectedZoneId={selectedZoneId}
            onSelect={handleSelectZone}
            panelOpen={panelOpen}
            onTogglePanel={() => setPanelOpen((open) => !open)}
          />
        </div>
      )}

      {detailZoneId != null && <ZoneDetailModal zoneId={detailZoneId} onClose={() => setDetailZoneId(null)} />}
      {detailEventId != null && <EventDetailModal eventId={detailEventId} onClose={() => setDetailEventId(null)} />}
      {detailRainfallId != null && (
        <RainfallObservationDetailModal observationId={detailRainfallId} onClose={() => setDetailRainfallId(null)} />
      )}
    </div>
  )
}

function ZoneListPanel({ zones, alertsByZoneId, selectedZoneId, onSelect, panelOpen, onTogglePanel }) {
  return (
    <div className="w-full shrink-0 lg:w-80">
      <button
        type="button"
        onClick={onTogglePanel}
        aria-expanded={panelOpen}
        aria-controls="zone-list-panel"
        className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-4 py-2.5 text-sm font-semibold text-slate-800 dark:text-slate-200 lg:hidden"
      >
        Zone List ({zones.length})
        <span aria-hidden="true">{panelOpen ? "▲" : "▼"}</span>
      </button>

      <div
        id="zone-list-panel"
        className={`mt-2 max-h-[70vh] overflow-y-auto rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 lg:mt-0 lg:block lg:max-h-[70vh] ${
          panelOpen ? "block" : "hidden"
        }`}
      >
        {zones.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400">No zones to show.</div>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {zones.map((zone) => {
              const alert = alertsByZoneId.get(zone.id)
              return (
                <li key={zone.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(zone.id)}
                    aria-current={selectedZoneId === zone.id ? "true" : undefined}
                    className={`w-full px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800 ${
                      selectedZoneId === zone.id ? "bg-slate-50 dark:bg-slate-800" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">{zone.name}</div>
                        <div className="truncate text-xs text-slate-500 dark:text-slate-400">{zone.state}</div>
                      </div>
                      <RiskBadge level={zone.risk_level} size="sm" />
                    </div>
                    <div className="mt-1.5 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                      <span>
                        {zone.risk_level === "UNKNOWN"
                          ? `${zone.historical_event_count ?? 0} historical event(s)`
                          : `Risk Score ${Number(zone.risk_score).toFixed(1)}`}
                      </span>
                      {alert && <span className="font-medium text-red-600 dark:text-red-400">Active Alert</span>}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
