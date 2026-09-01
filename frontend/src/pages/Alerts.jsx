import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import RiskBadge from "../components/RiskBadge"
import EmptyState from "../components/ui/EmptyState"
import ErrorState from "../components/ui/ErrorState"
import Loading from "../components/ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { acknowledgeAlert, getAlerts, getZones, resolveAlert } from "../services/api"
import { formatDateTime } from "../utils/riskUtils"

const SEVERITIES = ["ALL", "LOW", "MODERATE", "HIGH", "CRITICAL"]
const TABS = [
  { key: "active", label: "Active" },
  { key: "resolved", label: "History" },
]

const STATUS_STYLES = {
  active: "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400",
  acknowledged: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400",
  resolved: "border-slate-200 bg-slate-100 text-slate-500 dark:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:text-slate-500",
}

function AlertStatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        STATUS_STYLES[status] || STATUS_STYLES.active
      }`}
    >
      {status}
    </span>
  )
}

export default function Alerts() {
  const [tab, setTab] = useState("active")
  const alertsState = useApi(() => getAlerts(tab), [tab])
  const zonesState = useApi(getZones, [])
  const navigate = useNavigate()
  const [actionState, setActionState] = useState({ id: null, error: null })

  const [severity, setSeverity] = useState("ALL")
  const [location, setLocation] = useState("ALL")
  const [sinceDate, setSinceDate] = useState("")

  const zoneById = useMemo(() => {
    const map = new Map()
    for (const zone of zonesState.data || []) map.set(zone.id, zone)
    return map
  }, [zonesState.data])

  const locationOptions = useMemo(
    () => [...new Set((zonesState.data || []).map((zone) => zone.state))].sort(),
    [zonesState.data],
  )

  async function handleAcknowledge(id) {
    setActionState({ id, error: null })
    try {
      await acknowledgeAlert(id)
      alertsState.reload()
    } catch {
      setActionState({ id: null, error: "Could not acknowledge this alert right now." })
      return
    }
    setActionState({ id: null, error: null })
  }

  async function handleResolve(id) {
    setActionState({ id, error: null })
    try {
      await resolveAlert(id)
      alertsState.reload()
    } catch {
      setActionState({ id: null, error: "Could not resolve this alert right now." })
      return
    }
    setActionState({ id: null, error: null })
  }

  if (alertsState.loading) return <Loading variant="skeleton" rows={5} label="Loading alerts..." />
  if (alertsState.error) return <ErrorState onRetry={alertsState.reload} />

  const alerts = alertsState.data || []
  const filtered = alerts.filter((alert) => {
    if (severity !== "ALL" && alert.severity !== severity) return false
    if (location !== "ALL") {
      const zone = zoneById.get(alert.zone_id)
      if (!zone || zone.state !== location) return false
    }
    if (sinceDate) {
      const created = new Date(alert.created_at)
      if (created < new Date(sinceDate)) return false
    }
    return true
  })

  return (
    <div className="space-y-4">
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            aria-current={tab === t.key ? "true" : undefined}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-blue-600 text-blue-700 dark:border-blue-500 dark:text-blue-400"
                : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by severity">
          {SEVERITIES.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setSeverity(value)}
              aria-pressed={severity === value}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                severity === value
                  ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900"
                  : "border-slate-200 bg-white text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800"
              }`}
            >
              {value}
            </button>
          ))}
        </div>

        <select
          value={location}
          onChange={(event) => setLocation(event.target.value)}
          aria-label="Filter by location"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 dark:border-slate-700 dark:bg-slate-900"
        >
          <option value="ALL">All Locations</option>
          {locationOptions.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={sinceDate}
          onChange={(event) => setSinceDate(event.target.value)}
          aria-label="Show alerts on or after this date"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 dark:border-slate-700 dark:bg-slate-900"
        />

        <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">
          {filtered.length} of {alerts.length} shown
        </span>
      </div>

      {actionState.error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-400">
          {actionState.error}
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          title={alerts.length === 0 ? `No ${tab === "active" ? "active" : "historical"} alerts.` : "No alerts match these filters."}
          message={
            alerts.length === 0
              ? tab === "active"
                ? "No zone currently has an active landslide warning."
                : "No alerts have been resolved yet."
              : "Try clearing the severity, location, or date filter."
          }
        />
      ) : (
        <ul className="space-y-3">
          {filtered.map((alert) => {
            const zone = zoneById.get(alert.zone_id)
            return (
              <li key={alert.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <RiskBadge level={alert.severity} size="sm" />
                      <AlertStatusBadge status={alert.status} />
                      <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">{alert.title}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {zone ? `${zone.name} · ${zone.state}` : `Zone #${alert.zone_id}`}
                      {alert.risk_score != null ? (
                        <span className="ml-2 text-slate-400 dark:text-slate-500">Risk Score {Number(alert.risk_score).toFixed(1)}</span>
                      ) : (
                        zone && <span className="ml-2 text-slate-400 dark:text-slate-500">Risk Score {Number(zone.risk_score).toFixed(1)}</span>
                      )}
                    </div>
                  </div>
                  <span className="shrink-0 text-xs text-slate-400 dark:text-slate-500">{formatDateTime(alert.created_at)}</span>
                </div>

                <p className="mt-3 whitespace-pre-line text-sm text-slate-600 dark:text-slate-400">{alert.message}</p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => navigate(`/risk-map?zone=${alert.zone_id}`)}
                    className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    View on Map
                  </button>
                  {alert.status === "active" && (
                    <button
                      type="button"
                      onClick={() => handleAcknowledge(alert.id)}
                      disabled={actionState.id === alert.id}
                      className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400 dark:hover:bg-amber-900/40"
                    >
                      {actionState.id === alert.id ? "Acknowledging…" : "Acknowledge"}
                    </button>
                  )}
                  {alert.status !== "resolved" && (
                    <button
                      type="button"
                      onClick={() => handleResolve(alert.id)}
                      disabled={actionState.id === alert.id}
                      className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400 dark:hover:bg-emerald-900/40"
                    >
                      {actionState.id === alert.id ? "Resolving…" : "Resolve"}
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
