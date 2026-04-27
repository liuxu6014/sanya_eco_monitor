import test from 'node:test'
import assert from 'node:assert/strict'

import {
  clearRequestCache,
  readRequestCache,
  writeRequestCache,
} from '../src/utils/requestCache.js'


class MemoryStorage {
  constructor() {
    this.store = new Map()
  }

  getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null
  }

  setItem(key, value) {
    this.store.set(key, String(value))
  }

  removeItem(key) {
    this.store.delete(key)
  }
}


test('request cache reads from memory first', () => {
  globalThis.sessionStorage = new MemoryStorage()
  clearRequestCache()

  writeRequestCache('analysis-dashboard', { data: { value: 1 }, persist: true })
  const cached = readRequestCache('analysis-dashboard')

  assert.equal(cached.data.value, 1)
})

test('request cache falls back to sessionStorage', () => {
  globalThis.sessionStorage = new MemoryStorage()
  clearRequestCache()

  globalThis.sessionStorage.setItem(
    'request-cache:analysis-dashboard',
    JSON.stringify({
      data: { value: 2 },
      savedAt: Date.now(),
    }),
  )

  const cached = readRequestCache('analysis-dashboard')

  assert.equal(cached.data.value, 2)
})
