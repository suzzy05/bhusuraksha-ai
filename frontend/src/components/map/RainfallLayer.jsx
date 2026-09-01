import "leaflet.markercluster/dist/MarkerCluster.css"
import "leaflet.markercluster/dist/MarkerCluster.Default.css"
import L from "leaflet"
import "leaflet.markercluster"
import { useEffect, useRef } from "react"
import { useMap } from "react-leaflet"
import { createRainfallIcon } from "./mapIcons"

/**
 * Renders rainfall observations as a clustered layer — same imperative
 * leaflet.markercluster approach as HistoricalEventsLayer (kept as a
 * separate small component rather than a shared abstraction, since
 * rainfall readings are typically far denser per station than landslide
 * events and may need different clustering tuning later).
 */
export default function RainfallLayer({ observations, onViewDetails }) {
  const map = useMap()
  const clusterGroupRef = useRef(null)
  const onViewDetailsRef = useRef(onViewDetails)

  useEffect(() => {
    onViewDetailsRef.current = onViewDetails
  }, [onViewDetails])

  useEffect(() => {
    const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 60, showCoverageOnHover: false })
    clusterGroupRef.current = clusterGroup
    map.addLayer(clusterGroup)
    return () => {
      map.removeLayer(clusterGroup)
      clusterGroupRef.current = null
    }
  }, [map])

  useEffect(() => {
    const clusterGroup = clusterGroupRef.current
    if (!clusterGroup) return
    clusterGroup.clearLayers()

    for (const obs of observations) {
      if (obs.latitude == null || obs.longitude == null) continue
      const dateLabel = obs.observed_date ? new Date(obs.observed_date).toLocaleDateString() : "date not available"
      const amountLabel = obs.rainfall_mm == null ? "amount not available" : `${obs.rainfall_mm} mm`
      const marker = L.marker([obs.latitude, obs.longitude], {
        icon: createRainfallIcon(),
        title: `Rainfall observation — ${dateLabel} — ${amountLabel}`,
        alt: "Rainfall observation marker",
      })
      marker.on("click", () => onViewDetailsRef.current(obs.id))
      clusterGroup.addLayer(marker)
    }
  }, [observations])

  return null
}
