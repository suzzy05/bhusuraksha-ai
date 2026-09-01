import { useState } from "react"
import RiskFactors from "../components/risk/RiskFactors"
import RiskScore from "../components/risk/RiskScore"
import EmptyState from "../components/ui/EmptyState"
import ErrorState from "../components/ui/ErrorState"
import LoadingState from "../components/ui/LoadingState"
import { useApi } from "../hooks/useApi"
import { getZone, getZones, predictRisk } from "../services/api"
import { formatDateTime, sortByRisk } from "../utils/riskUtils"

export default function RiskIntelligence() {
  const zonesState = useApi(getZones, [])
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const effectiveZoneId = selectedZoneId ?? (zonesState.data ? sortByRisk(zonesState.data)[0]?.id ?? null : null)

  const zoneState = useApi(() => (effectiveZoneId != null ? getZone(effectiveZoneId) : Promise.resolve(null)), [
    effectiveZoneId,
  ])

  const predictionState = useApi(
    () => (zoneState.data ? predictRisk(zoneState.data.environment) : Promise.resolve(null)),
    [zoneState.data],
  )

  if (zonesState.loading) return <LoadingState variant="skeleton" rows={6} label="Loading zones..." />
  if (zonesState.error) return <ErrorState onRetry={zonesState.reload} />

  if (!zonesState.data || zonesState.data.length === 0) {
    return (
      <EmptyState
        title="No monitored zones available."
        message="Risk Intelligence explains predictions for existing zones — none are currently registered."
      />
    )
  }

  const zones = sortByRisk(zonesState.data)
  const prediction = predictionState.data

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 dark:text-slate-400 dark:border-slate-700 dark:bg-slate-900">
        Select a monitored zone to see exactly why its current risk prediction came out the way it did — the
        rule-based factor breakdown is specific to this zone's live inputs; model-level feature importance (shown
        only when the ML model is used) is not.
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <label htmlFor="zone-select" className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Zone
        </label>
        <select
          id="zone-select"
          value={effectiveZoneId ?? ""}
          onChange={(event) => setSelectedZoneId(Number(event.target.value))}
          className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:border-blue-400 dark:border-slate-700 dark:bg-slate-900"
        >
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name} ({zone.state}) — {zone.risk_level}
            </option>
          ))}
        </select>
      </div>

      {(zoneState.loading || predictionState.loading) && (
        <LoadingState variant="skeleton" rows={5} label="Loading risk explanation..." />
      )}

      {(zoneState.error || predictionState.error) && (
        <ErrorState
          title="Unable to load risk prediction."
          onRetry={() => {
            zoneState.reload()
            predictionState.reload()
          }}
        />
      )}

      {zoneState.data && prediction && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900 lg:col-span-2">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{zoneState.data.name}</h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              {zoneState.data.state} · Zone data last updated {formatDateTime(zoneState.data.updated_at)}
            </p>
            <div className="mt-4">
              <RiskScore
                score={prediction.risk_score}
                level={prediction.risk_level}
                predictionSource={prediction.prediction_source}
              />
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Risk Factors</h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Rule-based contribution breakdown, specific to this zone's current environmental inputs.
            </p>
            <div className="mt-4">
              <RiskFactors factors={prediction.risk_factors} />
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Model-Level Feature Importance</h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              From the trained RandomForest — describes the model overall, not this prediction.
            </p>
            <div className="mt-4">
              {prediction.feature_importance ? (
                <RiskFactors factors={prediction.feature_importance} modelLevel />
              ) : (
                <EmptyState
                  title="Not applicable."
                  message="This prediction used the rule-based fallback, which has no trained-model feature importance."
                />
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
