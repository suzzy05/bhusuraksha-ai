import { useMemo } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"
import EmptyState from "../components/ui/EmptyState"
import ErrorState from "../components/ui/ErrorState"
import Loading from "../components/ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { getDataSources, getDataStatus, getLandslideEvents, getRainfallObservations, getZone, getZones } from "../services/api"
import { RISK_CHART_COLORS, RISK_LEVELS } from "../utils/riskUtils"

// GET /zones only returns summary fields (no rainfall/environment), so the
// environmental comparison chart below fetches each zone's detail
// (GET /zones/{id}) to get real rainfall_24h values instead of guessing.
async function fetchZonesWithEnvironment() {
  const zones = await getZones()
  return Promise.all(zones.map((zone) => getZone(zone.id)))
}

function aggregateByState(events) {
  const counts = new Map()
  for (const event of events) {
    const key = event.state || "Unknown"
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return [...counts.entries()].map(([state, count]) => ({ state, count })).sort((a, b) => b.count - a.count)
}

function aggregateBySource(events, sourceNameById) {
  const counts = new Map()
  for (const event of events) {
    const key = event.source_id || "unknown"
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return [...counts.entries()]
    .map(([sourceId, count]) => ({ source: sourceNameById.get(sourceId) || sourceId, count }))
    .sort((a, b) => b.count - a.count)
}

function aggregateByStation(observations) {
  const counts = new Map()
  for (const obs of observations) {
    const key = obs.station_id || "Unknown station"
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return [...counts.entries()].map(([station, count]) => ({ station, count })).sort((a, b) => b.count - a.count)
}

function aggregateByYear(events) {
  const counts = new Map()
  for (const event of events) {
    if (!event.event_date) continue
    const year = new Date(event.event_date).getFullYear()
    if (Number.isNaN(year)) continue
    counts.set(year, (counts.get(year) || 0) + 1)
  }
  return [...counts.entries()].map(([year, count]) => ({ year: String(year), count })).sort((a, b) => a.year - b.year)
}

export default function Analytics() {
  const { data: zones, loading, error, reload } = useApi(fetchZonesWithEnvironment, [])
  const zoneList = zones || []

  const dataStatusState = useApi(getDataStatus, [])
  const sourcesRegistered = dataStatusState.data?.real_data?.sources_registered ?? 0
  // GET /landslides caps page_size at 200 (a deliberate bound — see Phase 10
  // spec: never pull an unbounded inventory to the browser), so analytics
  // summarizes at most the 200 most-recently-ingested events, never silently
  // truncated without disclosure (see the note rendered below).
  const EVENTS_SAMPLE_SIZE = 200
  const eventsState = useApi(
    () => (sourcesRegistered > 0 ? getLandslideEvents({ page_size: EVENTS_SAMPLE_SIZE }) : Promise.resolve(null)),
    [sourcesRegistered],
  )
  const events = eventsState.data?.results || []
  const eventsTotal = eventsState.data?.total ?? 0
  const eventsTruncated = eventsTotal > events.length
  const sourcesState = useApi(() => (sourcesRegistered > 0 ? getDataSources() : Promise.resolve(null)), [sourcesRegistered])
  const sourceNameById = useMemo(() => {
    const map = new Map()
    for (const source of sourcesState.data || []) map.set(source.source_id, source.name)
    return map
  }, [sourcesState.data])
  const eventsByState = useMemo(() => aggregateByState(events), [events])
  const eventsByYear = useMemo(() => aggregateByYear(events), [events])
  const eventsBySource = useMemo(() => aggregateBySource(events, sourceNameById), [events, sourceNameById])

  const rainfallRegistered = dataStatusState.data?.real_data?.rainfall_observations ?? 0
  const RAINFALL_SAMPLE_SIZE = 200
  const rainfallState = useApi(
    () => (rainfallRegistered > 0 ? getRainfallObservations({ page_size: RAINFALL_SAMPLE_SIZE }) : Promise.resolve(null)),
    [rainfallRegistered],
  )
  const rainfallObservations = rainfallState.data?.results || []
  const rainfallTotal = rainfallState.data?.total ?? 0
  const rainfallTruncated = rainfallTotal > rainfallObservations.length
  const rainfallByStation = useMemo(() => aggregateByStation(rainfallObservations), [rainfallObservations])

  const distribution = useMemo(
    () =>
      RISK_LEVELS.map((level) => ({ level, count: zoneList.filter((z) => z.risk_level === level).length })).filter(
        (entry) => entry.count > 0,
      ),
    [zoneList],
  )

  const byZone = useMemo(
    () => zoneList.map((z) => ({ name: z.name, risk_score: z.risk_score, risk_level: z.risk_level })),
    [zoneList],
  )

  const environmental = useMemo(
    () =>
      zoneList.map((z) => ({
        name: z.name,
        rainfall_24h: z.environment?.rainfall_24h,
        risk_score: z.risk_score,
        risk_level: z.risk_level,
      })),
    [zoneList],
  )

  if (loading) return <Loading label="Loading analytics..." />
  if (error) return <ErrorState onRetry={reload} />

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
        Zone risk scores are computed only where real terrain and live weather data exist for that zone;
        zones without real environmental coverage show as UNKNOWN rather than an estimated score.
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Risk Distribution</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Share of zones per risk level</p>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="count"
                  nameKey="level"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                  isAnimationActive={false}
                >
                  {distribution.map((entry) => (
                    <Cell key={entry.level} fill={RISK_CHART_COLORS[entry.level]} />
                  ))}
                </Pie>
                <Legend verticalAlign="bottom" height={24} />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Risk Score by Zone</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Current computed risk score (0-100)</p>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byZone} margin={{ left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "#64748b" }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  angle={-25}
                  textAnchor="end"
                  height={55}
                />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="risk_score" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {byZone.map((entry) => (
                    <Cell key={entry.name} fill={RISK_CHART_COLORS[entry.risk_level]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Rainfall (24h) vs Risk Score</h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Environmental comparison across monitored zones</p>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                type="number"
                dataKey="rainfall_24h"
                name="Rainfall (24h, mm)"
                tick={{ fontSize: 12, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="risk_score"
                name="Risk Score"
                domain={[0, 100]}
                tick={{ fontSize: 12, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
              />
              <ZAxis range={[90, 90]} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<EnvironmentalTooltip />} />
              <Scatter data={environmental} isAnimationActive={false}>
                {environmental.map((entry) => (
                  <Cell key={entry.name} fill={RISK_CHART_COLORS[entry.risk_level]} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Real Historical Data</h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          From registered, ingested datasets (<code>GET /landslides</code>) — distinct from the zone-level risk data above.
        </p>
        {eventsTruncated && (
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">
            Showing the {events.length} most-recently-ingested of {eventsTotal} total events — charts below
            summarize this sample, not the full inventory.
          </p>
        )}

        <div className="mt-4">
          {dataStatusState.loading && <Loading variant="skeleton" rows={3} label="Loading data status..." />}
          {dataStatusState.error && <ErrorState title="Unable to load data status." onRetry={dataStatusState.reload} />}

          {!dataStatusState.loading && !dataStatusState.error && sourcesRegistered === 0 && (
            <EmptyState
              title="No real historical datasets have been ingested yet."
              message="Register one via the backend CLI (scripts/ingest_dataset.py) to unlock historical-event analytics here."
            />
          )}

          {!dataStatusState.loading && !dataStatusState.error && sourcesRegistered > 0 && eventsState.loading && (
            <Loading variant="skeleton" rows={3} label="Loading historical events..." />
          )}
          {!dataStatusState.loading && !dataStatusState.error && sourcesRegistered > 0 && eventsState.error && (
            <ErrorState title="Unable to load historical events." onRetry={eventsState.reload} />
          )}

          {!dataStatusState.loading && !dataStatusState.error && sourcesRegistered > 0 && eventsState.data && (
            events.length === 0 ? (
              <EmptyState
                title="No historical events recorded."
                message="Real data sources are registered, but no event records have been ingested yet."
              />
            ) : (
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Events by State</h3>
                  <div className="mt-2 h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={eventsByState} margin={{ left: -10 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="state" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <Tooltip cursor={{ fill: "#f1f5f9" }} />
                        <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Events Over Time</h3>
                  <div className="mt-2 h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={eventsByYear} margin={{ left: -10 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <Tooltip cursor={{ fill: "#f1f5f9" }} />
                        <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Events by Source</h3>
                  <div className="mt-2 h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={eventsBySource} layout="vertical" margin={{ left: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis
                          type="category"
                          dataKey="source"
                          width={140}
                          tick={{ fontSize: 11, fill: "#64748b" }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip cursor={{ fill: "#f1f5f9" }} />
                        <Bar dataKey="count" fill="#2563eb" radius={[0, 4, 4, 0]} isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Real Rainfall Data</h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          From registered, ingested datasets (<code>GET /rainfall</code>) — raw historical observations, distinct
          from Phase 6's live weather.
        </p>
        {rainfallTruncated && (
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">
            Showing the {rainfallObservations.length} most-recently-ingested of {rainfallTotal} total observations.
          </p>
        )}

        <div className="mt-4">
          {dataStatusState.loading && <Loading variant="skeleton" rows={3} label="Loading data status..." />}
          {dataStatusState.error && <ErrorState title="Unable to load data status." onRetry={dataStatusState.reload} />}

          {!dataStatusState.loading && !dataStatusState.error && rainfallRegistered === 0 && (
            <EmptyState
              title="No real historical rainfall dataset has been ingested yet."
              message="Register one via the backend CLI (scripts/ingest_dataset.py --category rainfall) to unlock rainfall analytics here."
            />
          )}

          {!dataStatusState.loading && !dataStatusState.error && rainfallRegistered > 0 && rainfallState.loading && (
            <Loading variant="skeleton" rows={3} label="Loading rainfall observations..." />
          )}
          {!dataStatusState.loading && !dataStatusState.error && rainfallRegistered > 0 && rainfallState.error && (
            <ErrorState title="Unable to load rainfall observations." onRetry={rainfallState.reload} />
          )}

          {!dataStatusState.loading && !dataStatusState.error && rainfallRegistered > 0 && rainfallState.data && (
            rainfallObservations.length === 0 ? (
              <EmptyState
                title="No rainfall observations recorded."
                message="A rainfall data source is registered, but no observation records have been ingested yet."
              />
            ) : (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Observations by Station</h3>
                <div className="mt-2 h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={rainfallByStation} margin={{ left: -10 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="station" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: "#f1f5f9" }} />
                      <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-2 text-[11px] text-slate-400 dark:text-slate-500">
                  Accumulation windows (24h/72h/7d/30d) and an antecedent-rainfall index for a specific point are
                  available via <code>GET /rainfall/summary</code> — see the Risk Map's Rainfall layer.
                </p>
              </div>
            )
          )}
        </div>
      </section>
    </div>
  )
}

function EnvironmentalTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const point = payload[0].payload
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="font-semibold text-slate-800 dark:text-slate-200">{point.name}</div>
      <div className="text-slate-500 dark:text-slate-400">Rainfall 24h: {point.rainfall_24h} mm</div>
      <div className="text-slate-500 dark:text-slate-400">Risk score: {point.risk_score}</div>
    </div>
  )
}
