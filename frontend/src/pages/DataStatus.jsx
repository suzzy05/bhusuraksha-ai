import ErrorState from "../components/ui/ErrorState"
import LoadingState from "../components/ui/LoadingState"
import StatusBadge from "../components/ui/StatusBadge"
import { useApi } from "../hooks/useApi"
import { getDataStatus, getHealth } from "../services/api"
import { formatDateTime } from "../utils/riskUtils"

/**
 * A single System Status row. `status` is a StatusBadge key
 * (operational / degraded / unavailable / not_configured).
 */
function ServiceRow({ name, status, detail }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-0 dark:border-slate-800">
      <div className="min-w-0">
        <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{name}</div>
        {detail && <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{detail}</div>}
      </div>
      <StatusBadge status={status} />
    </div>
  )
}

const COVERAGE_STATUS_LABELS = {
  prototype: "Initial Deployment",
  partial_real_data: "Partial Regional Coverage",
  regional_real_data: "Regional Coverage",
  expanded_real_data: "Expanded Coverage",
}

function IndiaMonitoringCard({ indiaMonitoring }) {
  const {
    coverage_status: coverageStatus,
    real_data_sources: realDataSources,
    total_zones: totalZones,
    historical_events: historicalEvents,
  } = indiaMonitoring

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Pan-India Monitoring Architecture</h3>
        <span className="shrink-0 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400">
          {COVERAGE_STATUS_LABELS[coverageStatus] || coverageStatus}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Architecture for pan-India coverage exists; it does not claim landslide monitoring for every location in
        India — only where real data actually exists.
      </p>
      <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Registered Real Data Sources</div>
          <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{realDataSources}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Monitored Zones</div>
          <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{totalZones}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Historical Events</div>
          <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{historicalEvents}</div>
        </div>
      </div>
    </div>
  )
}

function healthLoadedStatus(health) {
  if (!health) return { backend: "unavailable", database: "unavailable", postgis: "unavailable" }

  const backend = health.status === "healthy" || health.status === "ok" ? "operational" : "degraded"
  const database = health.database?.connected ? "operational" : "unavailable"

  let postgis = "not_configured"
  if (health.database?.postgis) {
    postgis = health.database.postgis.available ? "operational" : "degraded"
  }

  return { backend, database, postgis }
}

export default function DataStatus() {
  const health = useApi(getHealth, [])
  const dataStatus = useApi(getDataStatus, [])

  const loading = health.loading || dataStatus.loading
  const error = health.error && dataStatus.error ? health.error : null

  if (loading) return <LoadingState variant="skeleton" rows={6} label="Loading system status..." />
  if (error) return <ErrorState title="Unable to reach the backend at all." onRetry={() => { health.reload(); dataStatus.reload() }} />

  const { backend, database, postgis } = healthLoadedStatus(health.data)
  const status = dataStatus.data

  const susceptibilityStatus = dataStatus.error
    ? "unavailable"
    : status?.susceptibility_model?.available
      ? "operational"
      : "not_configured"

  const weather = status?.live_weather
  const weatherStatus = dataStatus.error || !weather
    ? "unavailable"
    : !weather.provider_configured
      ? "not_configured"
      : weather.available
        ? "operational"
        : "degraded"

  const realSourcesCount = status?.real_data?.sources_registered ?? 0
  const realDataStatus = dataStatus.error ? "unavailable" : realSourcesCount > 0 ? "operational" : "not_configured"

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 dark:text-slate-400 dark:border-slate-700 dark:bg-slate-900">
        Every state below reflects an actual API response — a service is only marked{" "}
        <span className="font-semibold text-emerald-700 dark:text-emerald-400">Operational</span> once confirmed live, never assumed.
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Core Services</h2>
        <div className="mt-2">
          <ServiceRow name="Backend API" status={backend} detail={health.error ? "Unreachable" : `GET /health`} />
          <ServiceRow
            name="Database"
            status={database}
            detail={health.data?.database?.type ? `Type: ${health.data.database.type}` : undefined}
          />
          <ServiceRow
            name="PostGIS"
            status={postgis}
            detail={
              health.data?.database?.postgis?.version
                ? `Version ${health.data.database.postgis.version}`
                : postgis === "not_configured"
                  ? "SQLite dev database has no PostGIS extension"
                  : undefined
            }
          />
          <ServiceRow
            name="Susceptibility Model"
            status={susceptibilityStatus}
            detail={status?.susceptibility_model?.coverage || "Real presence/pseudo-absence model — GET /susceptibility"}
          />
          <ServiceRow
            name="Live Weather"
            status={weatherStatus}
            detail={
              weather?.last_refresh
                ? `Last successful refresh: ${formatDateTime(weather.last_refresh)}`
                : "Open-Meteo — no API key required"
            }
          />
          <ServiceRow
            name="Real Data Sources"
            status={realDataStatus}
            detail={`${realSourcesCount} source${realSourcesCount === 1 ? "" : "s"} registered — see Data Sources`}
          />
        </div>
      </section>

      {status?.india_monitoring && <IndiaMonitoringCard indiaMonitoring={status.india_monitoring} />}
    </div>
  )
}
