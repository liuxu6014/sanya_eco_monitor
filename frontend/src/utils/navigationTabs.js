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

export function tabHash(tab) {
  return `#${normalizeTab(tab)}`
}
