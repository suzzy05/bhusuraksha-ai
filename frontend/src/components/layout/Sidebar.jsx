import { NavLink } from "react-router-dom"

const NAV_SECTIONS = [
  {
    label: "OVERVIEW",
    items: [
      { to: "/", label: "Dashboard", end: true, icon: GridIcon },
      { to: "/risk-map", label: "Risk Map", icon: MapIcon },
      { to: "/alerts", label: "Alerts", icon: BellIcon },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { to: "/analytics", label: "Analytics", icon: ChartIcon },
      { to: "/risk-analysis", label: "Risk Analysis", icon: PulseIcon },
    ],
  },
  {
    label: "DATA",
    items: [
      { to: "/data-sources", label: "Data Sources", icon: DatabaseIcon },
      { to: "/data-status", label: "System Status", icon: ShieldIcon },
    ],
  },
]

export default function Sidebar({ open, collapsed, onNavigate, onToggleCollapse, online }) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-[1200] flex shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-slate-100 transition-all duration-200 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
        collapsed ? "lg:w-[76px]" : "lg:w-64"
      } w-64 ${open ? "translate-x-0" : "-translate-x-full"}`}
    >
      <div className="flex items-center gap-3 border-b border-slate-800 px-5 py-5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-blue-600 text-sm font-bold text-white">
          BS
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold tracking-wide text-white">BHUSURAKSHA AI</div>
            <div className="truncate text-[11px] text-slate-400">Predict. Warn. Protect.</div>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <div className="px-3 pb-1.5 text-[10px] font-semibold tracking-wider text-slate-500">
                {section.label}
              </div>
            )}
            <div className="space-y-1">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={onNavigate}
                  title={collapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      collapsed ? "justify-center" : ""
                    } ${
                      isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                    }`
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="hidden border-t border-slate-800 px-3 py-3 lg:block">
        <button
          type="button"
          onClick={onToggleCollapse}
          className="flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800/60 hover:text-white"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <CollapseIcon className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`} />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>

      <div className="border-t border-slate-800 px-5 py-4">
        <div className={`flex items-center gap-2 text-xs ${collapsed ? "justify-center" : ""}`}>
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              online === null ? "bg-slate-500" : online ? "bg-emerald-500" : "bg-red-500"
            }`}
          />
          {!collapsed && (
            <span className="text-slate-300">
              {online === null ? "Checking backend..." : online ? "System Online" : "Backend Offline"}
            </span>
          )}
        </div>
      </div>
    </aside>
  )
}

function GridIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  )
}

function MapIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-6-3V4l6 3m0 13l6-3m-6 3V7m6 10l6 3V6l-6-3m0 14V4m0 0L9 7" />
    </svg>
  )
}

function BellIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  )
}

function ChartIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18M8 17V10m5 7V6m5 11v-4" />
    </svg>
  )
}

function PulseIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h4l2-7 4 14 2-7h6" />
    </svg>
  )
}

function DatabaseIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path strokeLinecap="round" d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5" />
      <path strokeLinecap="round" d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3" />
    </svg>
  )
}

function ShieldIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.5 12l2 2 3.5-4" />
    </svg>
  )
}

function CollapseIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7m9 14l-7-7 7-7" />
    </svg>
  )
}
