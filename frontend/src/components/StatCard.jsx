const ACCENT_CLASSES = {
  slate: "text-slate-900 dark:text-slate-100",
  red: "text-red-600 dark:text-red-400",
  orange: "text-orange-600 dark:text-orange-400",
  blue: "text-blue-600 dark:text-blue-400",
}

export default function StatCard({ label, value, accent = "slate", description, unavailable = false }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</div>
      <div
        className={
          unavailable
            ? "mt-2 text-lg font-medium text-slate-400 dark:text-slate-500"
            : `mt-2 text-3xl font-semibold ${ACCENT_CLASSES[accent] || ACCENT_CLASSES.slate}`
        }
      >
        {unavailable ? "Unavailable" : value}
      </div>
      {description && <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{description}</div>}
    </div>
  )
}
