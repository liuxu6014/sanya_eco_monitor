export const DEFAULT_TAB = 'overview'
export const TAB_STORAGE_KEY = 'sanyaEcoActiveTab'

export const VALID_TABS = ['overview', 'analytics', 'special', 'reports']

export function normalizeTab(value) {
  return VALID_TABS.includes(value) ? value : DEFAULT_TAB
}

export function tabFromHash(hash) {
  const raw = String(hash || '').replace(/^#\/?/, '')
  return VALID_TABS.includes(raw) ? raw : null
}

export function tabFromPath(pathname) {
  const raw = String(pathname || '/').replace(/^\/+/, '').split('/')[0]
  if (!raw) {
    return DEFAULT_TAB
  }
  return VALID_TABS.includes(raw) ? raw : null
}

export function tabFromLocation(pathname, hash) {
  const pathTab = tabFromPath(pathname)
  if (pathTab && pathTab !== DEFAULT_TAB) {
    return pathTab
  }

  return tabFromHash(hash) || pathTab || DEFAULT_TAB
}

export function resolveInitialTab(pathname, hash, storedTab) {
  const pathTab = tabFromPath(pathname)
  const hashTab = tabFromHash(hash)

  if (pathTab && pathTab !== DEFAULT_TAB) {
    return pathTab
  }

  if (hashTab) {
    return hashTab
  }

  if (pathTab === DEFAULT_TAB) {
    return normalizeTab(storedTab)
  }

  return normalizeTab(storedTab)
}

export function tabPath(tab) {
  const normalized = normalizeTab(tab)
  return normalized === DEFAULT_TAB ? '/' : `/${normalized}`
}
