import { formatFieldLabel } from "../../utils/riskUtils"

function contributionLabel(fraction) {
  if (fraction >= 0.66) return "High contribution"
  if (fraction >= 0.33) return "Moderate contribution"
  return "Low contribution"
}

/**
 * Visual bar breakdown of risk_factors (or, when `modelLevel` is set, of a
 * RandomForest's global feature_importances_). `factors` is a flat
 * {name: number} map. Bars are scaled relative to the largest value in the
 * set, not to the risk score itself — this is a comparison of factors
 * against each other, not an absolute percentage.
 */
export default function RiskFactors({ factors, modelLevel = false }) {
  const entries = Object.entries(factors || {}).sort(([, a], [, b]) => b - a)
  const max = Math.max(...entries.map(([, value]) => value), 0.0001)

  if (entries.length === 0) return null

  return (
    <div className="space-y-3">
      {modelLevel && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400">
          Model-level feature importance — reflects the trained model overall, not an explanation of this specific
          prediction.
        </p>
      )}
      {entries.map(([name, value]) => {
        const fraction = value / max
        return (
          <div key={name}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-700 dark:text-slate-300">{formatFieldLabel(name)}</span>
              <span className="text-slate-400 dark:text-slate-500">{contributionLabel(fraction)}</span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                className={`h-full rounded-full ${modelLevel ? "bg-slate-400 dark:bg-slate-500" : "bg-blue-600 dark:bg-blue-500"}`}
                style={{ width: `${Math.max(fraction * 100, 4)}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
