import RiskBadge from "../RiskBadge"
import { RISK_CHART_COLORS } from "../../utils/riskUtils"

const SOURCE_LABELS = {
  machine_learning: "Machine Learning",
  rule_based_fallback: "Rule-based fallback",
}

/**
 * Large risk-score readout: numeric score, risk-level badge, and which
 * prediction path produced it (never hidden — a rule-based fallback must
 * never be presented as if it were the ML model).
 */
export default function RiskScore({ score, level, predictionSource }) {
  const color = RISK_CHART_COLORS[level] || "#64748b"

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-8">
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold tabular-nums" style={{ color }}>
          {Math.round(score)}
        </span>
        <span className="text-sm text-slate-400 dark:text-slate-500">/ 100</span>
      </div>
      <div className="flex flex-col gap-1.5">
        <RiskBadge level={level} />
        {predictionSource && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Source: <span className="font-medium text-slate-700 dark:text-slate-300">{SOURCE_LABELS[predictionSource] || predictionSource}</span>
          </span>
        )}
      </div>
    </div>
  )
}
