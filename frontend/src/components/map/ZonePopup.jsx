import RiskBadge from "../RiskBadge"
import { formatDateTime } from "../../utils/riskUtils"

export default function ZonePopup({ zone, alert, onViewDetails }) {
  return (
    <div className="min-w-[200px] space-y-2 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold text-slate-900 dark:text-slate-100">{zone.name}</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">{zone.state}</div>
        </div>
        <RiskBadge level={zone.risk_level} size="sm" />
      </div>

      {zone.risk_level === "UNKNOWN" ? (
        <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
          <span>Historical Events</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200">{zone.historical_event_count ?? 0} recorded</span>
        </div>
      ) : (
        <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
          <span>Risk Score</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200">{Number(zone.risk_score).toFixed(1)} / 100</span>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>Last Updated</span>
        <span>{formatDateTime(zone.updated_at)}</span>
      </div>

      {alert && (
        <div className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
          Active Alert · {alert.severity}
        </div>
      )}

      <button
        type="button"
        onClick={onViewDetails}
        className="w-full rounded-md border border-slate-300 bg-slate-900 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 dark:border-slate-600"
      >
        View Details
      </button>
    </div>
  )
}
