import { lazy, Suspense } from "react"
import { Route, Routes, useLocation } from "react-router-dom"
import AppShell from "./components/layout/AppShell"
import PageErrorBoundary from "./components/layout/PageErrorBoundary"
import RouteFallback from "./components/layout/RouteFallback"
import Dashboard from "./pages/Dashboard"
import NotFound from "./pages/NotFound"

// Dashboard is the initial page, so it stays eagerly bundled. Every other
// page — plus their heavy dependencies (Leaflet via Risk Map, Recharts via
// Analytics) — loads only once the user actually navigates there.
const RiskMap = lazy(() => import("./pages/RiskMap"))
const Alerts = lazy(() => import("./pages/Alerts"))
const Analytics = lazy(() => import("./pages/Analytics"))
const RiskIntelligence = lazy(() => import("./pages/RiskIntelligence"))
const DataSources = lazy(() => import("./pages/DataSources"))
const DataStatus = lazy(() => import("./pages/DataStatus"))

const PAGE_META = {
  "/": { title: "Dashboard", subtitle: "Live landslide risk overview" },
  "/risk-map": { title: "Risk Map", subtitle: "Interactive GIS view of monitored zones" },
  "/alerts": { title: "Alert Center", subtitle: "Active and historical landslide warnings" },
  "/analytics": { title: "Analytics", subtitle: "Risk trends across monitored zones" },
  "/risk-analysis": { title: "Risk Analysis", subtitle: "Why a zone's current risk prediction came out this way" },
  "/data-sources": { title: "Data Sources", subtitle: "Registered data sources and their provenance" },
  "/data-status": { title: "System Status", subtitle: "Backend, database, and data-pipeline health" },
}

export default function App() {
  const location = useLocation()
  const meta = PAGE_META[location.pathname] || { title: "BHUSURAKSHA AI" }

  return (
    <AppShell title={meta.title} subtitle={meta.subtitle}>
      <PageErrorBoundary key={location.pathname}>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/risk-map" element={<RiskMap />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/risk-analysis" element={<RiskIntelligence />} />
            <Route path="/data-sources" element={<DataSources />} />
            <Route path="/data-status" element={<DataStatus />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </PageErrorBoundary>
    </AppShell>
  )
}
