// Operational-status badge — distinct from RiskBadge, which encodes risk
// meaning (LOW/MODERATE/HIGH/CRITICAL). This encodes system/data health.
const STATUS_STYLES = {
  operational: { label: "Operational", className: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800" },
  available: { label: "Available", className: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800" },
  processed: { label: "Processed", className: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800" },
  degraded: { label: "Degraded", className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  processing: { label: "Processing", className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  configured: { label: "Configured", className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  credentials_required: { label: "Credentials Required", className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800" },
  unavailable: { label: "Unavailable", className: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800" },
  failed: { label: "Failed", className: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800" },
  download_failed: { label: "Download Failed", className: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800" },
  not_configured: { label: "Not Configured", className: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700" },
}

const DEFAULT_STYLE = { className: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700" }

/**
 * `status` should be one of STATUS_STYLES's keys (case-insensitive,
 * spaces/hyphens normalized to underscores). `label` overrides the display
 * text while keeping the color mapped from `status`.
 */
export default function StatusBadge({ status, label }) {
  const key = String(status || "").trim().toLowerCase().replace(/[\s-]+/g, "_")
  const style = STATUS_STYLES[key] || DEFAULT_STYLE
  const text = label || style.label || (status ? String(status) : "Unknown")

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${style.className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {text}
    </span>
  )
}
