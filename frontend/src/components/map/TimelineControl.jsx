const SPEED_OPTIONS = [
  { label: "1x", ms: 500 },
  { label: "2x", ms: 250 },
  { label: "4x", ms: 125 },
]

/**
 * Play/pause/scrub bar for EventAnimationLayer. Purely presentational —
 * state (stepIndex/playing/speed) lives in the page, matching the
 * page-owns-state convention the other map filters already use here.
 * Defaults to paused even when the layer is on, per the codebase's
 * existing aversion to auto-playing motion (Recharts animations are
 * disabled everywhere else in this app).
 */
export default function TimelineControl({
  stepIndex,
  stepCount,
  playing,
  speedMs,
  currentDateLabel,
  shownCount,
  totalCount,
  onPlayPause,
  onScrub,
  onSpeedChange,
  onReset,
}) {
  const disabled = stepCount === 0

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-3 py-2">
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Event timeline:</span>

      <button
        type="button"
        onClick={onPlayPause}
        disabled={disabled}
        className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-800"
      >
        {playing ? "Pause" : "Play"}
      </button>

      <button
        type="button"
        onClick={onReset}
        disabled={disabled}
        className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-800"
      >
        Reset
      </button>

      <input
        type="range"
        min={0}
        max={Math.max(stepCount - 1, 0)}
        value={Math.min(stepIndex, Math.max(stepCount - 1, 0))}
        disabled={disabled}
        onChange={(e) => onScrub(Number(e.target.value))}
        aria-label="Scrub through historical event timeline"
        className="h-1.5 w-40 accent-slate-600 disabled:opacity-50"
      />

      <select
        value={speedMs}
        onChange={(e) => onSpeedChange(Number(e.target.value))}
        disabled={disabled}
        aria-label="Playback speed"
        className="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-2 py-1 text-xs text-slate-700 dark:text-slate-300 disabled:opacity-50"
      >
        {SPEED_OPTIONS.map((opt) => (
          <option key={opt.ms} value={opt.ms}>
            {opt.label}
          </option>
        ))}
      </select>

      <span className="text-xs text-slate-400 dark:text-slate-500">
        {disabled
          ? "No dated events in view"
          : `${currentDateLabel || "—"} · ${shownCount} of ${totalCount} events shown`}
      </span>
    </div>
  )
}
