import { useState } from "react"
import DataSourceCard from "../components/data/DataSourceCard"
import ErrorState from "../components/ui/ErrorState"
import LoadingState from "../components/ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { getDataSource, getDataSourceQuality, getDataSources, getDataStatus } from "../services/api"
import { formatDateTime } from "../utils/riskUtils"

function SourceTypeBadge({ kind }) {
  const isDemo = kind === "demo"
  return (
    <span
      className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        isDemo
          ? "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400"
          : "border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-400"
      }`}
    >
      {isDemo ? "Demo / Synthetic" : "Real / External"}
    </span>
  )
}

const RUN_STATUS_LABELS = {
  registered: "Registered",
  validated: "Validated",
  processing: "Processing",
  processed: "Processed",
  failed: "Failed",
}

function statusDotColor(status) {
  if (status === "processed") return "bg-emerald-500"
  if (status === "failed") return "bg-red-500"
  if (status === "processing" || status === "validated") return "bg-amber-500"
  return "bg-slate-300"
}

function Row({ label, value, isLink, isError }) {
  if (!value) return null
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 dark:border-slate-800">
      <dt className="shrink-0 text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className={`text-right ${isError ? "text-red-600 dark:text-red-400" : "text-slate-800 dark:text-slate-200"}`}>
        {isLink ? (
          <a href={value} target="_blank" rel="noreferrer" className="break-all text-blue-600 underline">
            {value}
          </a>
        ) : (
          <span className="break-words">{value}</span>
        )}
      </dd>
    </div>
  )
}

function CompletenessRow({ label, count, total }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-600 dark:text-slate-400">{label}</span>
        <span className="text-slate-400 dark:text-slate-500">
          {count} / {total} ({pct}%)
        </span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-blue-600" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

const QUALITY_CATEGORIES = {
  historical_landslide: [
    ["Coordinates", "with_coordinates"],
    ["Event Date", "with_event_date"],
    ["State", "with_state"],
    ["District", "with_district"],
    ["Event Type", "with_event_type"],
    ["Severity", "with_severity"],
  ],
  rainfall: [
    ["Coordinates", "with_coordinates"],
    ["Observed Date", "with_observed_date"],
    ["Station ID", "with_station_id"],
    ["Rainfall Value", "with_rainfall_value"],
  ],
}

function DataCompletenessSection({ sourceId, category }) {
  const fields = QUALITY_CATEGORIES[category]
  const { data: quality, loading, error } = useApi(
    () => (fields ? getDataSourceQuality(sourceId) : Promise.resolve(null)),
    [sourceId, category],
  )

  if (!fields) return null
  if (loading) return <div className="text-xs text-slate-400 dark:text-slate-500">Loading data completeness…</div>
  if (error || !quality) return null
  if (quality.stored_records === 0) return null

  const total = quality.stored_records

  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Data Completeness</h4>
      <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
        How much of the schema this source's {total} stored record{total === 1 ? "" : "s"} actually populated — not
        a measure of scientific or prediction accuracy.
      </p>
      <div className="mt-3 space-y-2.5">
        {fields.map(([label, key]) => (
          <CompletenessRow key={key} label={label} count={quality[key]} total={total} />
        ))}
      </div>
    </div>
  )
}

function DataSourceDetailModal({ sourceId, onClose }) {
  const { data: source, loading, error, reload } = useApi(() => getDataSource(sourceId), [sourceId])

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
      >
        {loading && <LoadingState label="Loading data source..." />}
        {error && <ErrorState title="Could not load data source." onRetry={reload} />}

        {source && (
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{source.name}</h3>
                <p className="text-sm capitalize text-slate-500 dark:text-slate-400">{source.category.replace(/_/g, " ")}</p>
              </div>
              <SourceTypeBadge kind={source.source_type === "demo_synthetic" ? "demo" : "external"} />
            </div>

            <div className="flex items-center gap-2 text-sm">
              <span className={`h-2.5 w-2.5 rounded-full ${statusDotColor(source.last_status)}`} />
              <span className="font-medium text-slate-800 dark:text-slate-200">
                {RUN_STATUS_LABELS[source.last_status] || source.last_status}
              </span>
            </div>

            <dl className="space-y-2 text-sm">
              <Row label="Provider" value={source.provider} />
              <Row label="Source URL" value={source.official_source_url} isLink />
              <Row label="License" value={source.license} />
              <Row label="Citation" value={source.citation} />
              <Row label="Geographic Coverage" value={source.geographic_coverage} />
              <Row label="Temporal Coverage" value={source.temporal_coverage} />
              <Row label="Access Method" value={source.access_method} />
              <Row
                label="Checksum (SHA-256)"
                value={source.checksum_sha256 ? `${source.checksum_sha256.slice(0, 16)}…` : null}
              />
              <Row label="Registered" value={source.registered_at && formatDateTime(source.registered_at)} />
              <Row label="Last Processed" value={source.processed_at ? formatDateTime(source.processed_at) : "Never"} />
              <Row label="Last Error" value={source.last_error} isError />
              <Row label="Limitations" value={source.limitations} />
            </dl>

            <DataCompletenessSection sourceId={sourceId} category={source.category} />

            <p className="text-[11px] text-slate-400 dark:text-slate-500">
              This detail view never exposes filesystem paths or credentials — only provenance metadata.
            </p>

            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-md border border-slate-200 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function RegisteredSourcesSection() {
  const { data: sources, loading, error, reload } = useApi(getDataSources, [])
  const [selectedId, setSelectedId] = useState(null)

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Registered Data Sources</h3>
      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
        Ingested via the CLI (<code>scripts/ingest_dataset.py</code>) — this is CLI/admin-only architecture, not a
        public upload feature.
      </p>

      {loading && (
        <div className="mt-4">
          <LoadingState variant="skeleton" rows={3} label="Loading registered sources..." />
        </div>
      )}
      {error && (
        <div className="mt-4 flex items-center gap-3 text-xs text-red-500 dark:text-red-400">
          Could not load data sources.
          <button type="button" onClick={reload} className="font-medium underline">
            Retry
          </button>
        </div>
      )}

      {sources && sources.length === 0 && (
        <div className="mt-4 rounded-md border border-dashed border-slate-200 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No real data sources registered yet.
        </div>
      )}

      {sources && sources.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
          {sources.map((source) => (
            <li key={source.source_id}>
              <button
                type="button"
                onClick={() => setSelectedId(source.source_id)}
                className="flex w-full items-center justify-between gap-3 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{source.name}</div>
                  <div className="truncate text-xs capitalize text-slate-500 dark:text-slate-400">
                    {source.category.replace(/_/g, " ")}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <SourceTypeBadge kind={source.source_type === "demo_synthetic" ? "demo" : "external"} />
                  <span className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                    <span className={`h-2 w-2 rounded-full ${statusDotColor(source.last_status)}`} />
                    {RUN_STATUS_LABELS[source.last_status] || source.last_status}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selectedId != null && <DataSourceDetailModal sourceId={selectedId} onClose={() => setSelectedId(null)} />}
    </section>
  )
}

export default function DataSources() {
  const { data: status, loading, error, reload } = useApi(getDataStatus, [])

  if (loading) return <LoadingState variant="skeleton" rows={6} label="Loading data sources..." />
  if (error) return <ErrorState onRetry={reload} />

  const realData = status.real_data

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 dark:text-slate-400 dark:border-slate-700 dark:bg-slate-900">
        BHUSURAKSHA AI clearly separates <span className="font-semibold text-blue-700 dark:text-blue-400">demo / synthetic</span> data
        from <span className="font-semibold text-purple-700 dark:text-purple-400">real / external</span> data sources in every record —
        categories below show "Not Configured" unless a real dataset has actually been ingested.
      </div>

      <section>
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Data Categories</h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          Status per category, from <code>GET /data-status</code> and <code>GET /data-sources</code>. Availability
          here never implies India-wide coverage — only that this specific category has real data ingested.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DataSourceCard
            title="Historical Landslides"
            status={realData.landslide_events > 0 ? "available" : "not_configured"}
            description="Real registered landslide event records (date, location, source)."
            provider={status.external_landslide_data.configured ? "Configured" : undefined}
            count={realData.landslide_events}
          />
          <DataSourceCard
            title="Historical Rainfall"
            status={realData.rainfall_observations > 0 ? "available" : "not_configured"}
            description="Real registered precipitation observations."
            provider={status.external_rainfall_data.configured ? "Configured" : undefined}
            count={realData.rainfall_observations}
          />
          <DataSourceCard
            title="Terrain / DEM"
            status={realData.dem_available ? "available" : "not_configured"}
            description="Digital Elevation Model for slope/elevation."
            provider={status.external_dem_data.configured ? "Configured" : undefined}
          />
          <DataSourceCard
            title="Land Cover"
            status={realData.landcover_available ? "available" : "not_configured"}
            description="Vegetation / land-cover classification."
            provider={status.external_vegetation_data.configured ? "Configured" : undefined}
          />
          <DataSourceCard
            title="Administrative Boundaries"
            status={realData.boundaries_available ? "available" : "not_configured"}
            description="India / state / district boundary polygons, used for point-in-polygon enrichment."
          />
        </div>
      </section>

      <RegisteredSourcesSection />
    </div>
  )
}
