import ErrorState from "./ui/ErrorState"
import Loading from "./ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { getDataSource, getLandslideEvent } from "../services/api"
import { formatDateTime, formatFieldLabel } from "../utils/riskUtils"

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 dark:border-slate-800">
      <dt className="shrink-0 text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-right font-medium text-slate-800 dark:text-slate-200">{value ?? "Not available"}</dd>
    </div>
  )
}

/**
 * A historical observation, never a live risk prediction — this modal
 * never shows a risk score/level, and every field the source dataset
 * didn't actually provide reads "Not available" rather than being guessed
 * or shown as "Unknown".
 */
export default function EventDetailModal({ eventId, onClose }) {
  const { data: event, loading, error, reload } = useApi(() => getLandslideEvent(eventId), [eventId])
  const sourceState = useApi(
    () => (event?.source_id ? getDataSource(event.source_id) : Promise.resolve(null)),
    [event?.source_id],
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
        aria-label="Historical landslide event details"
      >
        {loading && <Loading label="Loading event details..." />}
        {error && <ErrorState title="Could not load event details." onRetry={reload} />}

        {event && (
          <div className="space-y-4">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                Historical Observation
              </span>
              <h3 className="mt-2 text-base font-semibold text-slate-900 dark:text-slate-100">Historical Landslide Event</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                A past recorded observation — not a current risk assessment for this location.
              </p>
            </div>

            <dl className="space-y-2 text-sm">
              <Row label="Event Date" value={event.event_date ? formatDateTime(event.event_date) : null} />
              <Row label="State" value={event.state} />
              <Row label="District" value={event.district} />
              <Row label="Event Type" value={event.event_type ? formatFieldLabel(event.event_type) : null} />
              <Row label="Severity" value={event.severity} />
              <Row label="Coordinates" value={`${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}`} />
              <Row
                label="Source Dataset"
                value={sourceState.data ? sourceState.data.name : event.source_id ? "Loading…" : null}
              />
              <Row label="Provider" value={sourceState.data?.provider} />
              <Row label="Record ID" value={event.source_record_id} />
              <Row label="Record Registered" value={formatDateTime(event.created_at)} />
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
