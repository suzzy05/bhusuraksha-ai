import { lazy, Suspense, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import AlertCard from "../components/AlertCard"
import RiskBadge from "../components/RiskBadge"
import StatCard from "../components/StatCard"
import ErrorState from "../components/ui/ErrorState"
import Loading from "../components/ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { getAlerts, getDataStatus, getIndiaSummary, getZones, refreshAllWeather } from "../services/api"
import { RISK_LEVELS, formatDateTime, isHighRisk, sortByRisk } from "../utils/riskUtils"

// Dashboard is eagerly loaded (it's the initial page), so its heaviest
// dependencies — Leaflet (via the map) and Recharts (via the distribution
// chart and zone detail modal) — are lazy-imported here instead of being
// pulled into the main bundle just because Dashboard is.
const RiskMapContainer = lazy(() => import("../components/map/RiskMapContainer"))
const RiskDistributionChart = lazy(() => import("../components/charts/RiskDistributionChart"))
const ZoneDetailModal = lazy(() => import("../components/ZoneDetailModal"))

const COVERAGE_STATUS_LABELS = {
  prototype: "Initial deployment",
  partial_real_data: "Partial regional coverage",
  regional_real_data: "Regional coverage",
  expanded_real_data: "Expanded coverage",
}

export default function Dashboard() {
  const zonesState = useApi(getZones, [])
  const alertsState = useApi(getAlerts, [])
  const indiaState = useApi(getIndiaSummary, [])
  const dataStatusState = useApi(getDataStatus, [])
  const [refreshState, setRefreshState] = useState({ status: "idle", result: null, error: null })
  const [detailZoneId, setDetailZoneId] = useState(null)

  const zones = zonesState.data || []
  const alerts = alertsState.data || []

  const alertsByZoneId = useMemo(() => {
    const map = new Map()
    for (const alert of alerts) {
      if (alert.zone_id != null && !map.has(alert.zone_id)) map.set(alert.zone_id, alert)
    }
    return map
  }, [alerts])

  const highRiskZones = useMemo(() => sortByRisk(zones.filter(isHighRisk)), [zones])
  const mapZones = useMemo(() => sortByRisk(zones), [zones])

  const distribution = useMemo(
    () => RISK_LEVELS.map((level) => ({ level, count: zones.filter((z) => z.risk_level === level).length })),
    [zones],
  )

  const recentAlerts = useMemo(
    () => [...alerts].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 4),
    [alerts],
  )

  function retry() {
    zonesState.reload()
    alertsState.reload()
  }

  async function handleRefreshEnvironmentalData() {
    setRefreshState({ status: "loading", result: null, error: null })
    try {
      const result = await refreshAllWeather()
      setRefreshState({ status: "done", result, error: null })
      zonesState.reload()
      alertsState.reload()
    } catch {
      setRefreshState({
        status: "done",
        result: null,
        error: "Could not refresh environmental data right now.",
      })
    }
  }

  if (zonesState.loading || alertsState.loading) return <Loading variant="skeleton" rows={8} label="Loading dashboard..." />
  if (zonesState.error || alertsState.error) {
    return <ErrorState onRetry={retry} />
  }

  const coverageStatus = indiaState.data?.coverage_status
  const liveWeather = dataStatusState.data?.live_weather
  const realSourcesCount = dataStatusState.data?.real_data?.sources_registered
  const referenceZoneCount = zones.filter((z) => z.source_type === "demo_seed").length
  const realZoneCount = zones.length - referenceZoneCount

  return (
    <div className="space-y-6">
      {/* 1. Situation overview */}
      <section>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">INDIA LANDSLIDE MONITORING</h1>
        <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">AI-powered environmental risk monitoring</p>
        <div className="mt-3 flex flex-col gap-3 rounded-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>
            <strong className="font-semibold text-slate-800 dark:text-slate-200">{COVERAGE_STATUS_LABELS[coverageStatus] || "Coverage status unavailable"}</strong>
            {" — "}{realZoneCount} zone{realZoneCount === 1 ? "" : "s"} derived from real historical data
            {referenceZoneCount > 0 && `, ${referenceZoneCount} reference zone${referenceZoneCount === 1 ? "" : "s"}`}.
            {" "}Every zone discloses its own data source — see Data Sources for details.
          </span>
          <button
            type="button"
            onClick={handleRefreshEnvironmentalData}
            disabled={refreshState.status === "loading"}
            className="shrink-0 rounded-md border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            {refreshState.status === "loading" ? "Refreshing…" : "Refresh Environmental Data"}
          </button>
        </div>

        {refreshState.status === "done" && refreshState.result && (
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-4 py-2 text-xs text-slate-600 dark:text-slate-400 dark:text-slate-500">
            <span>Zones Updated <strong className="text-slate-900 dark:text-slate-100">{refreshState.result.updated}</strong></span>
            <span>Risk Updates <strong className="text-slate-900 dark:text-slate-100">{refreshState.result.risk_updated}</strong></span>
            <span>Alerts Generated <strong className="text-slate-900 dark:text-slate-100">{refreshState.result.alerts_generated}</strong></span>
            <span>Weather Unavailable <strong className="text-slate-900 dark:text-slate-100">{refreshState.result.weather_unavailable}</strong></span>
          </div>
        )}
        {refreshState.status === "done" && refreshState.error && (
          <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-4 py-2 text-xs font-medium text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-400">
            {refreshState.error}
          </div>
        )}
      </section>

      {/* 2. Map / geographic context */}
      <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Geographic Overview</h2>
          <Link to="/risk-map" className="text-xs font-medium text-blue-600 hover:underline">
            Open Full Risk Map →
          </Link>
        </div>
        {zones.length === 0 ? (
          <div className="mt-3 rounded-md border border-dashed border-slate-200 dark:border-slate-700 py-14 text-center text-sm text-slate-500 dark:text-slate-400">
            No monitored zones available.
          </div>
        ) : (
          <div className="relative mt-3 h-72 overflow-hidden rounded-md border border-slate-200 dark:border-slate-700 sm:h-96">
            <Suspense fallback={<Loading variant="skeleton" rows={4} label="Loading map..." />}>
              <RiskMapContainer
                zones={mapZones}
                alertsByZoneId={alertsByZoneId}
                selectedZoneId={null}
                fitToken={0}
                onViewDetails={setDetailZoneId}
              />
            </Suspense>
          </div>
        )}
      </section>

      {/* 3. Alerts */}
      <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Recent Alerts</h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Most recently generated warnings</p>
          </div>
          <Link to="/alerts" className="text-xs font-medium text-blue-600 hover:underline">
            Alert Center →
          </Link>
        </div>

        {recentAlerts.length === 0 ? (
          <div className="mt-6 rounded-md border border-dashed border-slate-200 dark:border-slate-700 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            No active alerts.
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {recentAlerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </section>

      {/* 4. Supporting metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Active Alerts" value={alerts.length} accent="blue" />
        <StatCard label="Monitored Zones" value={zones.length} accent="slate" />
        <StatCard
          label="Live Weather"
          value={liveWeather?.available ? "Available" : "Not Yet Confirmed"}
          unavailable={dataStatusState.error}
          accent={liveWeather?.available ? "blue" : "slate"}
        />
        <StatCard
          label="Real Data Sources"
          value={realSourcesCount ?? 0}
          unavailable={dataStatusState.error}
          accent="slate"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-5 shadow-sm xl:col-span-2">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">High-Risk Zones</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Zones currently at HIGH or CRITICAL risk</p>

          {highRiskZones.length === 0 ? (
            <div className="mt-6 rounded-md border border-dashed border-slate-200 dark:border-slate-700 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
              No high-risk zones detected right now.
            </div>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-400 dark:text-slate-500">
                    <th className="pb-2 pr-4 font-medium">Zone</th>
                    <th className="pb-2 pr-4 font-medium">State</th>
                    <th className="pb-2 pr-4 font-medium">Risk Score</th>
                    <th className="pb-2 pr-4 font-medium">Risk Level</th>
                    <th className="pb-2 font-medium">Last Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {highRiskZones.map((zone) => (
                    <tr key={zone.id}>
                      <td className="py-2.5 pr-4 font-medium text-slate-800 dark:text-slate-200">{zone.name}</td>
                      <td className="py-2.5 pr-4 text-slate-500 dark:text-slate-400">{zone.state}</td>
                      <td className="py-2.5 pr-4 text-slate-700 dark:text-slate-300">{Number(zone.risk_score).toFixed(1)}</td>
                      <td className="py-2.5 pr-4">
                        <RiskBadge level={zone.risk_level} size="sm" />
                      </td>
                      <td className="py-2.5 text-slate-500 dark:text-slate-400">{formatDateTime(zone.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Risk Distribution</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Across all monitored zones</p>
          <div className="mt-4">
            <Suspense fallback={<Loading variant="skeleton" rows={4} label="Loading chart..." />}>
              <RiskDistributionChart distribution={distribution} />
            </Suspense>
          </div>
        </section>
      </div>

      <IndiaMonitoringOverview state={indiaState} totalZones={zones.length} realZoneCount={realZoneCount} referenceZoneCount={referenceZoneCount} />

      {detailZoneId != null && (
        <Suspense fallback={<ModalLoadingBackdrop />}>
          <ZoneDetailModal zoneId={detailZoneId} onClose={() => setDetailZoneId(null)} />
        </Suspense>
      )}
    </div>
  )
}

function ModalLoadingBackdrop() {
  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/50 px-4">
      <div className="flex items-center gap-3 rounded-lg bg-white px-6 py-5 text-sm text-slate-500 dark:text-slate-400 shadow-xl dark:bg-slate-900">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600 dark:border-slate-600 dark:border-t-slate-300" />
        Loading zone details...
      </div>
    </div>
  )
}

function IndiaMonitoringOverview({ state, totalZones, realZoneCount, referenceZoneCount }) {
  const { data, loading, error, reload } = state

  return (
    <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">India Monitoring Overview</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Pan-India landslide intelligence with detailed analysis where real data coverage actually exists —
            not a claim of nationwide monitoring.
          </p>
        </div>
        {data && (
          <span className="shrink-0 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400">
            {COVERAGE_STATUS_LABELS[data.coverage_status] || data.coverage_status}
          </span>
        )}
      </div>

      {loading && <div className="mt-4 text-xs text-slate-400 dark:text-slate-500">Loading India monitoring summary…</div>}
      {error && (
        <div className="mt-4 flex items-center gap-3 text-xs text-red-500 dark:text-red-400">
          Could not load India monitoring summary.
          <button type="button" onClick={reload} className="font-medium underline">
            Retry
          </button>
        </div>
      )}

      {data && !loading && (
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Monitored Zones</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{totalZones}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Derived from Real Events</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{realZoneCount}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Reference Zones</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{referenceZoneCount}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Historical Landslide Events</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{data.historical_landslide_events}</div>
          </div>
        </div>
      )}
    </section>
  )
}
