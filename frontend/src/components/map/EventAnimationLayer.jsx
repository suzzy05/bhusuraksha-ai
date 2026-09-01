import "leaflet.markercluster/dist/MarkerCluster.css"
import "leaflet.markercluster/dist/MarkerCluster.Default.css"
import L from "leaflet"
import "leaflet.markercluster"
import { useEffect, useMemo, useRef } from "react"
import { useMap } from "react-leaflet"
import { createHistoricalEventIcon } from "./mapIcons"

const STEP_COUNT = 60

/**
 * Chronological replay of REAL historical landslide events already fetched
 * for the map (the same `events` array HistoricalEventsLayer renders
 * statically) — never a fabricated slide-motion simulation. Every marker
 * traces back to a real `event_date`; nothing here implies prediction.
 *
 * One persistent markerClusterGroup (never recreated mid-playback). Markers
 * are pre-built once per `events` change and bucketed by real event_date
 * into STEP_COUNT equal time intervals; each step reveals its bucket via
 * batched `addLayers`, never per-event `addLayer` calls and never
 * `clearLayers()` on every tick (only on scrub-backward or a new event set).
 */
export default function EventAnimationLayer({ events, stepIndex, onStepCountChange, onViewDetails }) {
  const map = useMap()
  const clusterGroupRef = useRef(null)
  const onViewDetailsRef = useRef(onViewDetails)
  const lastAppliedStepRef = useRef(-1)

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

  const { buckets, stepCount } = useMemo(() => {
    const dated = events
      .filter((event) => event.latitude != null && event.longitude != null && event.event_date)
      .map((event) => ({ event, time: new Date(event.event_date).getTime() }))
      .filter((entry) => !Number.isNaN(entry.time))
      .sort((a, b) => a.time - b.time)

    if (dated.length === 0) return { buckets: [], stepCount: 0 }

    const minTime = dated[0].time
    const maxTime = dated[dated.length - 1].time
    const span = Math.max(maxTime - minTime, 1)
    const count = Math.min(STEP_COUNT, dated.length)

    const bucketArrays = Array.from({ length: count }, () => [])
    for (const { event, time } of dated) {
      const fraction = (time - minTime) / span
      const idx = Math.min(count - 1, Math.floor(fraction * count))
      const marker = L.marker([event.latitude, event.longitude], {
        icon: createHistoricalEventIcon(),
        title: `Historical landslide — ${new Date(event.event_date).toLocaleDateString()}`,
        alt: "Historical landslide event marker",
      })
      marker.on("click", () => onViewDetailsRef.current(event.id))
      bucketArrays[idx].push(marker)
    }
    return { buckets: bucketArrays, stepCount: count }
  }, [events])

  useEffect(() => {
    onStepCountChange(stepCount)
    lastAppliedStepRef.current = -1
    const clusterGroup = clusterGroupRef.current
    if (clusterGroup) clusterGroup.clearLayers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buckets])

  useEffect(() => {
    const clusterGroup = clusterGroupRef.current
    if (!clusterGroup || stepCount === 0) return
    const target = Math.max(0, Math.min(stepIndex, stepCount - 1))
    const last = lastAppliedStepRef.current

    if (target === last) return

    if (target === last + 1) {
      clusterGroup.addLayers(buckets[target])
    } else {
      clusterGroup.clearLayers()
      const upTo = buckets.slice(0, target + 1).flat()
      if (upTo.length > 0) clusterGroup.addLayers(upTo)
    }
    lastAppliedStepRef.current = target
  }, [stepIndex, buckets, stepCount])

  return null
}
