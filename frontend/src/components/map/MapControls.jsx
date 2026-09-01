const FILTERS = ["ALL", "LOW", "MODERATE", "HIGH", "CRITICAL"]

export default function MapControls({
  activeFilter,
  onFilterChange,
  onFitAll,
  resultCount,
  search,
  onSearchChange,
  stateFilter,
  onStateChange,
  stateOptions,
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search zone or location..."
          aria-label="Search zone or location"
          className="w-full min-w-[180px] flex-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-blue-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 sm:w-auto sm:flex-none"
        />

        <select
          value={stateFilter}
          onChange={(event) => onStateChange(event.target.value)}
          aria-label="Filter by state"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        >
          <option value="ALL">All States</option>
          {stateOptions.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={onFitAll}
          aria-label="Fit map to all visible zones"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Fit All Zones
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter zones by risk level">
          {FILTERS.map((level) => (
            <button
              key={level}
              type="button"
              aria-pressed={activeFilter === level}
              onClick={() => onFilterChange(level)}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                activeFilter === level
                  ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              {level}
            </button>
          ))}
        </div>

        <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">
          {resultCount} zone{resultCount === 1 ? "" : "s"} shown
        </span>
      </div>
    </div>
  )
}
