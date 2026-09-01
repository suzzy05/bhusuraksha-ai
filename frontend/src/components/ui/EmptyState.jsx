/**
 * Reusable empty state — used whenever real data honestly doesn't exist yet
 * (never render a fake chart/placeholder number instead of this).
 */
export default function EmptyState({ icon, title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-14 text-center dark:border-slate-700 dark:bg-slate-900">
      {icon && <div className="mb-1 text-slate-400 dark:text-slate-500">{icon}</div>}
      <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</div>
      {message && <div className="max-w-md text-sm text-slate-500 dark:text-slate-400">{message}</div>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
