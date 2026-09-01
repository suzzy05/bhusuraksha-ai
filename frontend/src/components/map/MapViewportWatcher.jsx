import { useEffect } from "react"
import { useMapEvents } from "react-leaflet"

/**
 * Reports the map's current viewport bounds to the parent whenever a pan/
 * zoom settles, plus once on mount — used to drive a bounded
 * GET /landslides/map query instead of ever fetching the whole inventory.
 */
export default function MapViewportWatcher({ onBoundsChange }) {
  const map = useMapEvents({
    moveend: () => onBoundsChange(map.getBounds()),
    zoomend: () => onBoundsChange(map.getBounds()),
  })

  useEffect(() => {
    onBoundsChange(map.getBounds())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return null
}
