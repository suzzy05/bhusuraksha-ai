import { forwardRef } from "react"
import { Marker, Popup, Tooltip } from "react-leaflet"
import { createRiskIcon } from "./mapIcons"
import ZonePopup from "./ZonePopup"

const RiskMarker = forwardRef(function RiskMarker({ zone, alert, isSelected, onViewDetails }, ref) {
  if (zone.latitude == null || zone.longitude == null) return null

  return (
    <Marker
      ref={ref}
      position={[zone.latitude, zone.longitude]}
      icon={createRiskIcon(zone.risk_level, { selected: isSelected })}
      title={`${zone.name} — ${zone.risk_level || "Unknown"} risk, score ${Number(zone.risk_score).toFixed(1)}`}
      alt={`${zone.name} risk marker`}
    >
      <Tooltip direction="top" offset={[0, -4]}>
        {zone.name} · {zone.risk_level} · {Number(zone.risk_score).toFixed(1)}
      </Tooltip>
      <Popup minWidth={220}>
        <ZonePopup zone={zone} alert={alert} onViewDetails={() => onViewDetails(zone.id)} />
      </Popup>
    </Marker>
  )
})

export default RiskMarker
