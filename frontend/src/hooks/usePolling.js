import { useState, useEffect, useCallback } from 'react'

export function usePolling(fetchFn, intervalMs = 30000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetch = useCallback(async () => {
    try {
      const result = await fetchFn()
      setData(result)
      setLastUpdated(new Date())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [fetchFn])

  useEffect(() => {
    fetch()
    const timer = setInterval(fetch, intervalMs)
    return () => clearInterval(timer)
  }, [fetch, intervalMs])

  return { data, loading, error, lastUpdated, refetch: fetch }
}
