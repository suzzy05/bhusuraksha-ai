export const RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "CRITICAL"]

const RISK_RANK = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3 }

export function riskLevelRank(level) {
  return RISK_RANK[level] ?? 99
}

export function sortByRisk(zones) {
  return [...zones].sort((a, b) => {
    const rankDiff = riskLevelRank(a.risk_level) - riskLevelRank(b.risk_level)
    if (rankDiff !== 0) return rankDiff
    return (b.risk_score ?? 0) - (a.risk_score ?? 0)
  })
}

export function isHighRisk(zone) {
  return zone.risk_level === "HIGH" || zone.risk_level === "CRITICAL"
}

// Tailwind utility classes for badges, keyed by risk level.
export const RISK_BADGE_STYLES = {
  LOW: { badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800", dot: "bg-emerald-500" },
  MODERATE: { badge: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800", dot: "bg-amber-500" },
  HIGH: { badge: "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-800", dot: "bg-orange-500" },
  CRITICAL: { badge: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800", dot: "bg-red-500" },
}

const DEFAULT_BADGE_STYLE = { badge: "bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700", dot: "bg-slate-400" }

export function riskBadgeStyle(level) {
  return RISK_BADGE_STYLES[level] || DEFAULT_BADGE_STYLE
}

// Hex colors for chart fills, keyed by risk level.
export const RISK_CHART_COLORS = {
  LOW: "#10b981",
  MODERATE: "#d97706",
  HIGH: "#ea580c",
  CRITICAL: "#dc2626",
}

export function formatDateTime(value) {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
}

export function formatFieldLabel(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())
}
