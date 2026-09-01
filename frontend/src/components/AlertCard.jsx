import { formatDateTime } from "../utils/riskUtils"
import RiskBadge from "./RiskBadge"

export default function AlertCard({ alert, zoneName }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{alert.title}</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">{zoneName || `Zone #${alert.zone_id}`}</div>
        </div>
        <RiskBadge level={alert.severity} size="sm" />
      </div>
      <p className="mt-2 whitespace-pre-line text-sm text-slate-600 dark:text-slate-300">{alert.message}</p>
      <div className="mt-3 text-xs text-slate-400 dark:text-slate-500">{formatDateTime(alert.created_at)}</div>
    </div>
  )
}
