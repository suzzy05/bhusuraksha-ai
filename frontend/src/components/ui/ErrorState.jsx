export default function ErrorState({
  title = "Unable to connect to BHUSURAKSHA backend.",
  message,
  onRetry,
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-200 bg-red-50 px-6 py-14 text-center dark:border-red-900 dark:bg-red-950">
      <div className="text-sm font-semibold text-red-700 dark:text-red-400">{title}</div>
      {message && <div className="max-w-md text-sm text-red-600 dark:text-red-400">{message}</div>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-md border border-red-300 bg-white px-4 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-slate-900 dark:text-red-400 dark:hover:bg-red-900/40"
        >
          Retry
        </button>
      )}
    </div>
  )
}
