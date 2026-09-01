import LoadingState from "../ui/LoadingState"

/**
 * Suspense fallback for a lazy-loaded route. Renders inside AppShell's
 * <main> — the sidebar and topbar stay mounted and interactive while this
 * shows, so navigation never produces a blank screen.
 */
export default function RouteFallback() {
  return <LoadingState variant="skeleton" rows={6} label="Loading page..." />
}
