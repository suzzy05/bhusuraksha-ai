const LAYERS = [
  { key: "risk_zones", label: "Risk Zones", available: true },
  { key: "alerts", label: "Alerts", available: true },
  { key: "historical_landslides", label: "Historical Landslides", available: true },
  { key: "event_animation", label: "Event Timeline Animation", available: true },
  { key: "rainfall", label: "Rainfall", available: true },
  { key: "terrain", label: "Terrain", available: false },
  { key: "land_cover", label: "Land Cover", available: false },
]

/**
 * Layer toggle list. Layers backed by real data (`available: true`) are
 * interactive; the rest are shown disabled with "No data available" rather
 * than silently omitted or faked with placeholder content.
 */
export default function MapLayers({ activeLayers, onToggle }) {
  return (
    <div className="space-y-1.5" role="group" aria-label="Map layers">
      {LAYERS.map((layer) => {
        const on = activeLayers.has(layer.key)
        return (
          <label
            key={layer.key}
            className={`flex items-center justify-between gap-2 rounded-md border px-3 py-1.5 text-xs ${
              layer.available
                ? "cursor-pointer border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                : "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-600"
            }`}
          >
            <span className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={layer.available ? on : false}
                disabled={!layer.available}
                onChange={() => layer.available && onToggle(layer.key)}
                className="h-3.5 w-3.5"
              />
              {layer.label}
            </span>
            {!layer.available && <span className="text-[10px] italic">No data available</span>}
          </label>
        )
      })}
    </div>
  )
}
