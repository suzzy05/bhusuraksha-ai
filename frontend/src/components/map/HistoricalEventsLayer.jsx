import "leaflet.markercluster/dist/MarkerCluster.css"
import "leaflet.markercluster/dist/MarkerCluster.Default.css"
import L from "leaflet"
import "leaflet.markercluster"
import { useEffect, useRef } from "react"
import { useMap } from "react-leaflet"
import { createHistoricalEventIcon } from "./mapIcons"

/**
 * Renders historical landslide events as a clustered layer (leaflet's own
 * markercluster plugin, used imperatively — matching how MapController
 * already drives the underlying Leaflet map directly). Clicking an event
 * calls onViewDetails(event.id); clicking a cluster zooms in, which is
 * leaflet.markercluster's default built-in behavior.
 */
export default function HistoricalEventsLayer({ events, onViewDetails }) {
  const map = useMap()
  const clusterGroupRef = useRef(null)
  const onViewDetailsRef = useRef(onViewDetails)

  useEffect(() => {
    onViewDetailsRef.current = onViewDetails
  }, [onViewDetails])

  useEffect(() => {
    const clusterGroup = L.markerClusterGroup({ maxClusterRadius: 50, showCoverageOnHover: false })
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

    for (const event of events) {
      if (event.latitude == null || event.longitude == null) continue
      const dateLabel = event.event_date ? new Date(event.event_date).toLocaleDateString() : "date not available"
      const marker = L.marker([event.latitude, event.longitude], {
        icon: createHistoricalEventIcon(),
        title: `Historical landslide — ${dateLabel}`,
        alt: "Historical landslide event marker",
      })
      marker.on("click", () => onViewDetailsRef.current(event.id))
      clusterGroup.addLayer(marker)
    }
  }, [events])

  return null
}
