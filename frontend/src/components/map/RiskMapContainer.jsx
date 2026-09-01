import "leaflet/dist/leaflet.css"
import { useEffect, useMemo, useRef } from "react"
import { MapContainer, TileLayer, useMap } from "react-leaflet"
import EventAnimationLayer from "./EventAnimationLayer"
import HistoricalEventsLayer from "./HistoricalEventsLayer"
import MapViewportWatcher from "./MapViewportWatcher"
import RainfallLayer from "./RainfallLayer"
import "./mapIcons"
import RiskMarker from "./RiskMarker"

// Only used as the initial camera position before GET /zones resolves —
// real zone coordinates always take over via MapController's fit-to-bounds
// effect below, so this is never treated as a marker location.
const INDIA_CENTROID = [22.9734, 78.6569]
const DEFAULT_ZOOM = 5
const SINGLE_ZONE_ZOOM = 10
const SELECTED_ZONE_ZOOM = 10

function zonePoints(zones) {
  const points = zones
    .filter((zone) => zone.latitude != null && zone.longitude != null)
    .map((zone) => [zone.latitude, zone.longitude])
  return points.length > 0 ? points : null
}

function MapController({ zones, fitToken, selectedZoneId, markerRefs }) {
  const map = useMap()
  const visibleKey = useMemo(() => zones.map((zone) => zone.id).sort((a, b) => a - b).join(","), [zones])

  useEffect(() => {
    const points = zonePoints(zones)
    if (!points) return

    if (points.length === 1) {
      map.setView(points[0], SINGLE_ZONE_ZOOM)
    } else {
      map.fitBounds(points, { padding: [48, 48], maxZoom: 12 })
    }
    // Re-fit whenever the visible zone set changes (e.g. a risk filter) or
    // the user clicks "Fit All Zones" (fitToken) — not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleKey, fitToken])

  useEffect(() => {
    if (selectedZoneId == null) return
    const zone = zones.find((z) => z.id === selectedZoneId)
    if (!zone || zone.latitude == null || zone.longitude == null) return

    map.flyTo([zone.latitude, zone.longitude], Math.max(map.getZoom(), SELECTED_ZONE_ZOOM), { duration: 0.6 })
    markerRefs.current[zone.id]?.openPopup()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedZoneId])

  return null
}

export default function RiskMapContainer({
  zones,
  alertsByZoneId,
  selectedZoneId,
  fitToken,
  onViewDetails,
  historicalEvents = null,
  onViewHistoricalEvent,
  eventAnimationOn = false,
  animationStepIndex = 0,
  onAnimationStepCountChange,
  rainfallObservations = null,
  onViewRainfallObservation,
  onBoundsChange,
}) {
  const markerRefs = useRef({})

  return (
    <MapContainer center={INDIA_CENTROID} zoom={DEFAULT_ZOOM} scrollWheelZoom className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {zones.map((zone) => (
        <RiskMarker
          key={zone.id}
          ref={(instance) => {
            if (instance) markerRefs.current[zone.id] = instance
            else delete markerRefs.current[zone.id]
          }}
          zone={zone}
          alert={alertsByZoneId.get(zone.id)}
          isSelected={zone.id === selectedZoneId}
          onViewDetails={onViewDetails}
        />
      ))}

      <MapController zones={zones} fitToken={fitToken} selectedZoneId={selectedZoneId} markerRefs={markerRefs} />

      {onBoundsChange && <MapViewportWatcher onBoundsChange={onBoundsChange} />}
      {historicalEvents != null && eventAnimationOn && (
        <EventAnimationLayer
          events={historicalEvents}
          stepIndex={animationStepIndex}
          onStepCountChange={onAnimationStepCountChange}
          onViewDetails={onViewHistoricalEvent}
        />
      )}
      {historicalEvents != null && !eventAnimationOn && (
        <HistoricalEventsLayer events={historicalEvents} onViewDetails={onViewHistoricalEvent} />
      )}
      {rainfallObservations != null && (
        <RainfallLayer observations={rainfallObservations} onViewDetails={onViewRainfallObservation} />
      )}
    </MapContainer>
  )
}
