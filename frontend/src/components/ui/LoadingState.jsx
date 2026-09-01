/**
 * Spinner variant for small/inline loads, and a `skeleton` variant (rows of
 * pulsing bars) for page-level loads where a blank page would otherwise
 * flash before data arrives.
 */
export default function LoadingState({ label = "Loading...", variant = "spinner", rows = 4 }) {
  if (variant === "skeleton") {
    return (
      <div className="animate-pulse space-y-3 rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900" role="status" aria-label={label}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-4 rounded bg-slate-200 dark:bg-slate-700" style={{ width: `${85 - i * 12}%` }} />
        ))}
        <span className="sr-only">{label}</span>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500 dark:text-slate-400" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600 dark:border-slate-600 dark:border-t-slate-300" />
      <span className="text-sm">{label}</span>
    </div>
  )
}
