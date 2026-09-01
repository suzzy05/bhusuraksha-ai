import { riskBadgeStyle } from "../utils/riskUtils"

export default function RiskBadge({ level, size = "md" }) {
  const style = riskBadgeStyle(level)
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border font-semibold uppercase tracking-wide ${style.badge} ${sizeClasses}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {level || "UNKNOWN"}
    </span>
  )
}
