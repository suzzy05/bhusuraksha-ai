import { RISK_LEVELS, riskBadgeStyle } from "../../utils/riskUtils"

export default function MapLegend({ showHistorical = false, showAnimation = false, showRainfall = false }) {
  return (
    <div className="pointer-events-auto rounded-lg border border-slate-200 bg-white/95 p-3 text-xs shadow-md backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
      <div className="mb-2 font-semibold text-slate-700 dark:text-slate-200">Risk Level</div>
      <ul className="space-y-1.5">
        {RISK_LEVELS.map((level) => (
          <li key={level} className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${riskBadgeStyle(level).dot}`} aria-hidden="true" />
            <span className="text-slate-600 dark:text-slate-300">{level}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 max-w-[180px] text-[11px] leading-snug text-slate-400 dark:text-slate-500">
        Classification is calculated by the BHUSURAKSHA backend risk engine, not assigned manually.
      </p>

      {showHistorical && (
        <>
          <div className="mt-3 border-t border-slate-100 pt-2 font-semibold text-slate-700 dark:border-slate-800 dark:text-slate-200">Historical</div>
          <div className="mt-1.5 flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 bg-slate-500"
              style={{ transform: "rotate(45deg)" }}
              aria-hidden="true"
            />
            <span className="text-slate-600 dark:text-slate-300">Past landslide event</span>
          </div>
          <p className="mt-1.5 max-w-[180px] text-[11px] leading-snug text-slate-400 dark:text-slate-500">
            A historical observation, not a current risk assessment.
          </p>
          {showAnimation && (
            <p className="mt-1.5 max-w-[180px] text-[11px] leading-snug text-slate-400 dark:text-slate-500">
              Events revealed in chronological order — a real subset of the full record, not a prediction.
            </p>
          )}
        </>
      )}

      {showRainfall && (
        <>
          <div className="mt-3 border-t border-slate-100 pt-2 font-semibold text-slate-700 dark:border-slate-800 dark:text-slate-200">Rainfall</div>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm bg-sky-500" aria-hidden="true" />
            <span className="text-slate-600 dark:text-slate-300">Rainfall observation</span>
          </div>
          <p className="mt-1.5 max-w-[180px] text-[11px] leading-snug text-slate-400 dark:text-slate-500">
            A single historical reading, not a live forecast.
          </p>
        </>
      )}
    </div>
  )
}
