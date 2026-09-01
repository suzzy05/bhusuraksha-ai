import { useState } from "react"
import { useHealthStatus } from "../../hooks/useApi"
import { useTheme } from "../../hooks/useTheme"
import AssistantWidget from "./AssistantWidget"
import Sidebar from "./Sidebar"
import Topbar from "./Topbar"

export default function AppShell({ title, subtitle, lastUpdated, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  // Polled once here and shared — Sidebar and Topbar both display it, and
  // each polling independently would double every GET /health request.
  const online = useHealthStatus()
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 lg:flex">
      <Sidebar
        open={sidebarOpen}
        collapsed={collapsed}
        online={online}
        onNavigate={() => setSidebarOpen(false)}
        onToggleCollapse={() => setCollapsed((v) => !v)}
      />

      {sidebarOpen && (
        // Transparent, not dimmed — the dashboard/map behind the drawer
        // must stay fully visible. This is only a click-outside-to-close
        // catcher, not a darkening backdrop.
        <div
          className="fixed inset-0 z-[1150] lg:hidden"
          onClick={() => setSidebarOpen(false)}
          role="presentation"
        />
      )}

      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar
          title={title}
          subtitle={subtitle}
          lastUpdated={lastUpdated}
          online={online}
          theme={theme}
          onToggleTheme={toggleTheme}
          onMenuClick={() => setSidebarOpen((v) => !v)}
        />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>

      <AssistantWidget />
    </div>
  )
}
