import { useState, useEffect, useCallback } from 'react'
import {
  getInflightRequest,
  readRequestCache,
  setInflightRequest,
  writeRequestCache,
} from '../utils/requestCache.js'

export function usePolling(fetchFn, intervalMs = 30000, options = {}) {
  const {
    cacheKey = '',
    persist = false,
    staleMs = intervalMs,
    enabled = true,
  } = options

  const initialCache = cacheKey ? readRequestCache(cacheKey) : null
  const [data, setData] = useState(initialCache?.data ?? null)
  const [loading, setLoading] = useState(!initialCache)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(
    initialCache?.savedAt ? new Date(initialCache.savedAt) : null,
  )

  const fetch = useCallback(async ({ force = false } = {}) => {
    const cached = cacheKey ? readRequestCache(cacheKey) : null
    if (cached) {
      setData(cached.data)
      setLastUpdated(new Date(cached.savedAt))
      setLoading(false)
      setError(null)
      if (!force && Date.now() - cached.savedAt < staleMs) {
        return cached.data
      }
    } else {
      setLoading(true)
    }

    const inflight = !force && cacheKey ? getInflightRequest(cacheKey) : null
    if (inflight) {
      const deduped = await inflight
      setData(deduped)
      setLastUpdated(new Date())
      setLoading(false)
      setError(null)
      return deduped
    }

    const run = async () => {
      const result = await fetchFn()
      if (cacheKey) {
        writeRequestCache(cacheKey, { data: result, persist })
      }
      setData(result)
      setLastUpdated(new Date())
      setError(null)
      setLoading(false)
      return result
    }

    try {
      if (cacheKey) {
        return await setInflightRequest(cacheKey, run())
      }
      return await run()
    } catch (e) {
      setError(e.message)
      setLoading(false)
      throw e
    }
  }, [cacheKey, fetchFn, persist, staleMs])

  useEffect(() => {
    if (!enabled) {
      return undefined
    }

    fetch().catch(() => {})
    const timer = setInterval(() => {
      fetch({ force: true }).catch(() => {})
    }, intervalMs)
    return () => clearInterval(timer)
  }, [enabled, fetch, intervalMs])

  return {
    data,
    loading,
    error,
    lastUpdated,
    refetch: () => fetch({ force: true }),
  }
}
