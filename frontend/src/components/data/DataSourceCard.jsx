import StatusBadge from "../ui/StatusBadge"
import { formatDateTime } from "../../utils/riskUtils"

/**
 * One category card on the Data Sources page (Historical Landslides,
 * Rainfall, Terrain/DEM, Land Cover, Administrative Boundaries). `status`
 * should be "available" | "not_configured" (StatusBadge keys).
 */
export default function DataSourceCard({
  title,
  status,
  description,
  provider,
  coverage,
  lastProcessed,
  count,
  onClick,
}) {
  const clickable = typeof onClick === "function"
  const Wrapper = clickable ? "button" : "div"

  return (
    <Wrapper
      type={clickable ? "button" : undefined}
      onClick={onClick}
      className={`flex w-full flex-col gap-3 rounded-lg border border-slate-200 bg-white p-5 text-left shadow-sm dark:border-slate-700 dark:bg-slate-900 ${
        clickable ? "cursor-pointer transition-colors hover:border-slate-300 hover:bg-slate-50 dark:hover:border-slate-600 dark:hover:bg-slate-800" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
        <StatusBadge status={status} />
      </div>
      {description && <p className="text-xs leading-snug text-slate-500 dark:text-slate-400">{description}</p>}

      <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        {provider && (
          <div>
            <dt className="text-slate-400 dark:text-slate-500">Provider</dt>
            <dd className="mt-0.5 truncate font-medium text-slate-700 dark:text-slate-300">{provider}</dd>
          </div>
        )}
        {coverage && (
          <div>
            <dt className="text-slate-400 dark:text-slate-500">Coverage</dt>
            <dd className="mt-0.5 truncate font-medium text-slate-700 dark:text-slate-300">{coverage}</dd>
          </div>
        )}
        {typeof count === "number" && (
          <div>
            <dt className="text-slate-400 dark:text-slate-500">Records</dt>
            <dd className="mt-0.5 font-medium text-slate-700 dark:text-slate-300">{count.toLocaleString()}</dd>
          </div>
        )}
        <div>
          <dt className="text-slate-400 dark:text-slate-500">Last Processed</dt>
          <dd className="mt-0.5 font-medium text-slate-700 dark:text-slate-300">
            {lastProcessed ? formatDateTime(lastProcessed) : "Never"}
          </dd>
        </div>
      </dl>
    </Wrapper>
  )
}
