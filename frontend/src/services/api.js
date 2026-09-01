import axios from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export async function getHealth() {
  const { data } = await apiClient.get("/health")
  return data
}

export async function getZones() {
  const { data } = await apiClient.get("/zones")
  return data
}

export async function getZone(id) {
  const { data } = await apiClient.get(`/zones/${id}`)
  return data
}

export async function getAlerts(status) {
  const { data } = await apiClient.get("/alerts", { params: status ? { status } : undefined })
  return data
}

export async function acknowledgeAlert(id) {
  const { data } = await apiClient.post(`/alerts/${id}/acknowledge`)
  return data
}

export async function resolveAlert(id) {
  const { data } = await apiClient.post(`/alerts/${id}/resolve`)
  return data
}

export async function predictRisk(payload) {
  const { data } = await apiClient.post("/predict-risk", payload)
  return data
}

export async function getDataStatus() {
  const { data } = await apiClient.get("/data-status")
  return data
}

export async function getWeather(zoneId) {
  const { data } = await apiClient.get(`/weather/${zoneId}`)
  return data
}

export async function refreshWeather(zoneId) {
  const { data } = await apiClient.post(`/weather/${zoneId}/refresh`)
  return data
}

export async function refreshAllWeather() {
  // Sequentially fetches live weather for every zone server-side, so this
  // can take longer than the default timeout.
  const { data } = await apiClient.post("/weather/refresh-all", null, { timeout: 30000 })
  return data
}

export async function getWeatherHistory(zoneId, limit) {
  const { data } = await apiClient.get(`/weather/${zoneId}/history`, {
    params: limit ? { limit } : undefined,
  })
  return data
}

export async function getIndiaSummary() {
  const { data } = await apiClient.get("/india/summary")
  return data
}

export async function getLandslideEvents(params) {
  const { data } = await apiClient.get("/landslides", { params })
  return data
}

export async function getLandslideEvent(id) {
  const { data } = await apiClient.get(`/landslides/${id}`)
  return data
}

export async function getLandslidesInBbox(params) {
  const { data } = await apiClient.get("/landslides/map", { params })
  return data
}

export async function getNearbyLandslides(params) {
  const { data } = await apiClient.get("/landslides/nearby", { params })
  return data
}

export async function getDataSourceQuality(sourceId) {
  const { data } = await apiClient.get(`/data-sources/${encodeURIComponent(sourceId)}/quality`)
  return data
}

export async function getRainfallObservations(params) {
  const { data } = await apiClient.get("/rainfall", { params })
  return data
}

export async function getRainfallObservation(id) {
  const { data } = await apiClient.get(`/rainfall/${id}`)
  return data
}

export async function getRainfallInBbox(params) {
  const { data } = await apiClient.get("/rainfall/map", { params })
  return data
}

export async function getNearbyRainfall(params) {
  const { data } = await apiClient.get("/rainfall/nearby", { params })
  return data
}

export async function getRainfallSummary(params) {
  const { data } = await apiClient.get("/rainfall/summary", { params })
  return data
}

export async function getRainfallHistory(params) {
  const { data } = await apiClient.get("/rainfall/history", { params })
  return data
}

export async function getTerrainFeatures(params) {
  const { data } = await apiClient.get("/terrain/features", { params })
  return data
}

export async function getLandcover(params) {
  const { data } = await apiClient.get("/landcover", { params })
  return data
}

export async function getDataSources(params) {
  const { data } = await apiClient.get("/data-sources", { params })
  return data
}

export async function getDataSource(sourceId) {
  const { data } = await apiClient.get(`/data-sources/${encodeURIComponent(sourceId)}`)
  return data
}

export async function getDataSourceStatus(sourceId) {
  const { data } = await apiClient.get(`/data-sources/${encodeURIComponent(sourceId)}/status`)
  return data
}

export async function askAssistant(question) {
  const { data } = await apiClient.get("/assistant/ask", { params: { q: question } })
  return data
}
