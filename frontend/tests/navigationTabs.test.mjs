import test from 'node:test'
import assert from 'node:assert/strict'

import {
  DEFAULT_TAB,
  normalizeTab,
  tabFromHash,
  tabHash,
} from '../src/utils/navigationTabs.js'


test('normalizes invalid tabs to overview', () => {
  assert.equal(normalizeTab('analytics'), 'analytics')
  assert.equal(normalizeTab('bad-tab'), DEFAULT_TAB)
  assert.equal(normalizeTab(null), DEFAULT_TAB)
})

test('reads tab from hash', () => {
  assert.equal(tabFromHash('#analytics'), 'analytics')
  assert.equal(tabFromHash('#/reports'), 'reports')
  assert.equal(tabFromHash('#unknown'), null)
  assert.equal(tabFromHash(''), null)
})

test('writes normalized tab hash', () => {
  assert.equal(tabHash('reports'), '#reports')
  assert.equal(tabHash('unknown'), '#overview')
})
