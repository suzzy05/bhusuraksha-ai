import { Component } from "react"
import { Link } from "react-router-dom"

/**
 * Catches a rendering error in one page so it can't take down the whole
 * app shell (sidebar/topbar stay mounted and usable). App.jsx remounts this
 * per route via a `key={location.pathname}` prop, so navigating away also
 * clears the error automatically, in addition to the manual retry below.
 */
export default class PageErrorBoundary extends Component {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    // Logged for local debugging only — never rendered to the user (no
    // stack traces, no internal error details in the UI).
    console.error("Page render error:", error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-200 bg-red-50 px-6 py-14 text-center dark:border-red-900 dark:bg-red-950">
        <div className="text-sm font-semibold text-red-700 dark:text-red-400">Something went wrong.</div>
        <div className="max-w-md text-sm text-red-600 dark:text-red-400">Unable to render this page.</div>
        <div className="mt-2 flex items-center gap-3">
          <button
            type="button"
            onClick={() => this.setState({ hasError: false })}
            className="rounded-md border border-red-300 bg-white px-4 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-slate-900 dark:text-red-400 dark:hover:bg-red-900/40"
          >
            Try Again
          </button>
          <Link
            to="/"
            className="rounded-md border border-slate-200 bg-white px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    )
  }
}
