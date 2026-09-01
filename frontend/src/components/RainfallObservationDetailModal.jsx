import ErrorState from "./ui/ErrorState"
import Loading from "./ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { getDataSource, getRainfallObservation } from "../services/api"
import { formatDateTime } from "../utils/riskUtils"

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 dark:border-slate-800">
      <dt className="shrink-0 text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-right font-medium text-slate-800 dark:text-slate-200">{value ?? "Not available"}</dd>
    </div>
  )
}

/**
 * A raw historical rainfall reading — not a live weather forecast and not
 * a risk assessment. Missing fields read "Not available", never guessed.
 */
export default function RainfallObservationDetailModal({ observationId, onClose }) {
  const { data: observation, loading, error, reload } = useApi(
    () => getRainfallObservation(observationId),
    [observationId],
  )
  const sourceState = useApi(
    () => (observation?.source_id ? getDataSource(observation.source_id) : Promise.resolve(null)),
    [observation?.source_id],
  )

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/50 px-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-slate-900"
        onClick={(evt) => evt.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Rainfall observation details"
      >
        {loading && <Loading label="Loading observation details..." />}
        {error && <ErrorState title="Could not load observation details." onRetry={reload} />}

        {observation && (
          <div className="space-y-4">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                Historical Observation
              </span>
              <h3 className="mt-2 text-base font-semibold text-slate-900 dark:text-slate-100">Rainfall Observation</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                A single historical reading — not a live forecast or risk assessment.
              </p>
            </div>

            <dl className="space-y-2 text-sm">
              <Row label="Date" value={observation.observed_date ? formatDateTime(observation.observed_date) : null} />
              <Row label="Rainfall" value={observation.rainfall_mm != null ? `${observation.rainfall_mm} mm` : null} />
              <Row label="Station ID" value={observation.station_id} />
              <Row label="Coordinates" value={`${observation.latitude.toFixed(4)}, ${observation.longitude.toFixed(4)}`} />
              <Row
                label="Source Dataset"
                value={sourceState.data ? sourceState.data.name : observation.source_id ? "Loading…" : null}
              />
              <Row label="Provider" value={sourceState.data?.provider} />
              <Row label="Record Registered" value={formatDateTime(observation.created_at)} />
            </dl>

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
