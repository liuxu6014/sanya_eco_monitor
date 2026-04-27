const STORAGE_PREFIX = 'request-cache:'

const memoryCache = new Map()
const inflightRequests = new Map()

function storageKey(key) {
  return `${STORAGE_PREFIX}${key}`
}

function storageRef() {
  return typeof globalThis !== 'undefined' ? globalThis.sessionStorage : undefined
}

function canUseSessionStorage() {
  return typeof storageRef() !== 'undefined'
}

export function readRequestCache(key) {
  if (!key) {
    return null
  }

  const memoryValue = memoryCache.get(key)
  if (memoryValue) {
    return memoryValue
  }

  if (!canUseSessionStorage()) {
    return null
  }

  try {
    const raw = storageRef().getItem(storageKey(key))
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw)
    memoryCache.set(key, parsed)
    return parsed
  } catch {
    return null
  }
}

export function writeRequestCache(key, { data, persist = false, savedAt = Date.now() }) {
  if (!key) {
    return null
  }

  const entry = { data, savedAt }
  memoryCache.set(key, entry)

  if (persist && canUseSessionStorage()) {
    try {
      storageRef().setItem(storageKey(key), JSON.stringify(entry))
    } catch {}
  }

  return entry
}

export function clearRequestCache(key) {
  if (!key) {
    memoryCache.clear()
    inflightRequests.clear()
    return
  }

  memoryCache.delete(key)
  inflightRequests.delete(key)

  if (canUseSessionStorage()) {
    try {
      storageRef().removeItem(storageKey(key))
    } catch {}
  }
}

export function getInflightRequest(key) {
  if (!key) {
    return null
  }
  return inflightRequests.get(key) || null
}

export function setInflightRequest(key, promise) {
  if (!key) {
    return promise
  }

  inflightRequests.set(key, promise)
  promise.finally(() => {
    if (inflightRequests.get(key) === promise) {
      inflightRequests.delete(key)
    }
  })
  return promise
}
