import { useCallback, useEffect, useRef, useState } from "react"
import { getHealth } from "../services/api"

/**
 * Runs `fetcher()` and tracks loading/error/data state. Re-runs whenever
 * `deps` changes, and exposes `reload()` for manual retry buttons.
 */
export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const latestRequestId = useRef(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const load = useCallback(() => {
    const requestId = ++latestRequestId.current
    setLoading(true)
    setError(null)

    fetcherRef.current()
      .then((result) => {
        if (requestId === latestRequestId.current) {
          setData(result)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (requestId === latestRequestId.current) {
          setError(err)
          setLoading(false)
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, reload: load }
}

/**
 * Polls GET /health to drive the sidebar's backend status indicator.
 * Returns null while the first check is in flight, then true/false.
 */
export function useHealthStatus(intervalMs = 15000) {
  const [online, setOnline] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        await getHealth()
        if (!cancelled) setOnline(true)
      } catch {
        if (!cancelled) setOnline(false)
      }
    }

    check()
    const id = setInterval(check, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [intervalMs])

  return online
}
