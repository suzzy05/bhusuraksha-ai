import { useState } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Bar,
  BarChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import ErrorState from "./ui/ErrorState"
import Loading from "./ui/LoadingState"
import RiskBadge from "./RiskBadge"
import { useApi } from "../hooks/useApi"
import { getWeather, getWeatherHistory, getZone, refreshWeather } from "../services/api"
import { formatDateTime, formatFieldLabel } from "../utils/riskUtils"

export default function ZoneDetailModal({ zoneId, onClose }) {
  const { data: zone, loading, error, reload } = useApi(() => getZone(zoneId), [zoneId])

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/50 px-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-slate-900"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={zone ? `${zone.name} zone details` : "Zone details"}
      >
        {loading && <Loading label="Loading zone details..." />}
        {error && <ErrorState title="Could not load zone details." onRetry={reload} />}

        {zone && (
          <div className="space-y-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{zone.name}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">{zone.state}</p>
              </div>
              <RiskBadge level={zone.risk_level} />
            </div>

            {zone.risk_level === "UNKNOWN" ? (
              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-800/50">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-semibold text-slate-900 dark:text-slate-100">{zone.historical_event_count ?? 0}</span>
                  <span className="text-sm text-slate-500 dark:text-slate-400">real historical event(s) recorded</span>
                </div>
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                  This zone was derived from real historical landslide records for {zone.state}. No real
                  rainfall/terrain data is configured for this area yet, so no current risk score is
                  computed — showing a fabricated score here would be worse than showing none.
                </p>
              </div>
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-semibold text-slate-900 dark:text-slate-100">{zone.risk_score}</span>
                  <span className="text-sm text-slate-500 dark:text-slate-400">/ 100 risk score</span>
                </div>

                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Environmental Data</h4>
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    {Object.entries(zone.environment || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between border-b border-slate-100 pb-1 dark:border-slate-800">
                        <dt className="text-slate-500 dark:text-slate-400">{formatFieldLabel(key)}</dt>
                        <dd className="font-medium text-slate-800 dark:text-slate-200">{value == null ? "—" : String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                </div>

                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Risk Factors</h4>
                  <dl className="mt-2 space-y-2 text-sm">
                    {Object.entries(zone.risk_factors || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between">
                        <dt className="text-slate-500 dark:text-slate-400">{formatFieldLabel(key)}</dt>
                        <dd className="font-medium text-slate-800 dark:text-slate-200">{value == null ? "—" : value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </>
            )}

            <LiveWeatherSection zoneId={zoneId} onZoneUpdated={reload} />

            <WeatherHistorySection zoneId={zoneId} />

            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-md border border-slate-200 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function LiveWeatherSection({ zoneId, onZoneUpdated }) {
  const { data, loading, error, reload } = useApi(() => getWeather(zoneId), [zoneId])
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState(null)

  async function handleRefresh() {
    setRefreshing(true)
    setRefreshError(null)
    try {
      await refreshWeather(zoneId)
      await Promise.all([reload(), onZoneUpdated()])
    } catch {
      setRefreshError("Could not refresh live weather right now.")
    } finally {
      setRefreshing(false)
    }
  }

  const weather = data?.weather

  return (
    <div>
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Live Weather</h4>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing || loading}
          aria-label="Refresh live weather for this zone"
          className="rounded-md border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {refreshing ? "Refreshing…" : "Refresh Weather"}
        </button>
      </div>

      {loading && <div className="mt-2 text-xs text-slate-400 dark:text-slate-500">Loading live weather…</div>}
      {error && <div className="mt-2 text-xs text-red-500 dark:text-red-400">Could not load live weather.</div>}
      {refreshError && <div className="mt-2 text-xs text-red-500 dark:text-red-400">{refreshError}</div>}

      {weather && !loading && (
        <>
          {weather.available ? (
            <dl className="mt-2 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Temperature</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {weather.temperature == null ? "—" : `${weather.temperature} °C`}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Humidity</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {weather.humidity == null ? "—" : `${weather.humidity}%`}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Rainfall (24h)</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">
                  {weather.rainfall_24h == null ? "—" : `${weather.rainfall_24h} mm`}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Last Observation</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">{weather.observed_at || "—"}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Data Source</dt>
                <dd className="font-medium text-slate-800 dark:text-slate-200">{weather.source || "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Live weather currently unavailable.</p>
          )}
        </>
      )}
    </div>
  )
}

function WeatherHistorySection({ zoneId }) {
  const { data: history, loading, error } = useApi(() => getWeatherHistory(zoneId, 20), [zoneId])

  if (loading) return null
  if (error) return null

  const observations = history || []
  const chartData = [...observations].reverse().map((obs) => ({
    time: obs.observed_at || formatDateTime(obs.created_at),
    temperature: obs.temperature,
    humidity: obs.humidity,
    rainfall_24h: obs.rainfall_24h,
  }))

  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Weather History</h4>

      {chartData.length < 2 ? (
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          No weather history yet — refresh weather above to start recording observations.
        </p>
      ) : (
        <div className="mt-3 space-y-4">
          <MiniLineChart title="Temperature (°C)" dataKey="temperature" data={chartData} color="#ea580c" />
          <MiniLineChart title="Humidity (%)" dataKey="humidity" data={chartData} color="#2563eb" />
          <MiniBarChart title="Rainfall 24h (mm)" dataKey="rainfall_24h" data={chartData} color="#0ea5e9" />
        </div>
      )}
    </div>
  )
}

function MiniLineChart({ title, dataKey, data, color }) {
  return (
    <div>
      <div className="mb-1 text-xs text-slate-500 dark:text-slate-400">{title}</div>
      <div className="h-24">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis width={28} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={{ r: 2 }}
              isAnimationActive={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function MiniBarChart({ title, dataKey, data, color }) {
  return (
    <div>
      <div className="mb-1 text-xs text-slate-500 dark:text-slate-400">{title}</div>
      <div className="h-24">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis width={28} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Bar dataKey={dataKey} fill={color} radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
