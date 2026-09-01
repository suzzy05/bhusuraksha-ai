import L from "leaflet"
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png"
import markerIcon from "leaflet/dist/images/marker-icon.png"
import markerShadow from "leaflet/dist/images/marker-shadow.png"
import { RISK_CHART_COLORS } from "../../utils/riskUtils"

// Vite doesn't serve Leaflet's default marker images from the path Leaflet
// expects by default, which normally shows up as a broken/missing marker
// icon. Re-pointing them at the Vite-resolved asset URLs fixes it for any
// marker that ends up using the default L.Icon (we use custom divIcons
// below, but this keeps the default icon correct too, defensively).
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const SIZE_BY_LEVEL = { LOW: 16, MODERATE: 20, HIGH: 24, CRITICAL: 28 }
const DEFAULT_SIZE = 18
const DEFAULT_COLOR = "#64748b"

/**
 * A risk-colored circular marker icon. Risk is encoded by color AND size
 * (higher risk = larger marker), and every marker also carries a `title`
 * (set by the caller via the Leaflet `title` option) plus an in-map
 * tooltip/popup — so risk is never communicated by color alone.
 */
// A historical event is an observation, not a current risk — deliberately
// NOT circular or risk-colored (never confusable with the live risk
// markers above). A neutral slate diamond.
export function createHistoricalEventIcon() {
  const size = 12
  const total = size + 6
  return L.divIcon({
    className: "bhusuraksha-historical-marker",
    html: `<span style="display:block;width:${size}px;height:${size}px;background:#64748b;border:2px solid #ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.45);transform:rotate(45deg);"></span>`,
    iconSize: [total, total],
    iconAnchor: [total / 2, total / 2],
    popupAnchor: [0, -total / 2],
  })
}

// A rainfall observation is a raw historical reading, not a risk marker
// or a landslide event — a small blue square keeps it visually distinct
// from both the historical-landslide diamond and the risk circles.
export function createRainfallIcon() {
  const size = 10
  const total = size + 6
  return L.divIcon({
    className: "bhusuraksha-rainfall-marker",
    html: `<span style="display:block;width:${size}px;height:${size}px;background:#0ea5e9;border:2px solid #ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.45);border-radius:2px;"></span>`,
    iconSize: [total, total],
    iconAnchor: [total / 2, total / 2],
    popupAnchor: [0, -total / 2],
  })
}

export function createRiskIcon(level, { selected = false } = {}) {
  const color = RISK_CHART_COLORS[level] || DEFAULT_COLOR
  const size = SIZE_BY_LEVEL[level] || DEFAULT_SIZE
  const ringWidth = selected ? 4 : 2
  const ringColor = selected ? "#0f172a" : "#ffffff"
  const total = size + ringWidth * 2

  return L.divIcon({
    className: "bhusuraksha-risk-marker",
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:9999px;background:${color};border:${ringWidth}px solid ${ringColor};box-shadow:0 1px 4px rgba(15,23,42,0.45);"></span>`,
    iconSize: [total, total],
    iconAnchor: [total / 2, total / 2],
    popupAnchor: [0, -total / 2],
    tooltipAnchor: [0, -total / 2],
  })
}
