import test from 'node:test'
import assert from 'node:assert/strict'

import {
  DEFAULT_TAB,
  normalizeTab,
  resolveInitialTab,
  tabFromHash,
  tabFromLocation,
  tabFromPath,
  tabPath,
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

test('reads tab from path under /sanya base', () => {
  assert.equal(tabFromPath('/sanya/analytics'), 'analytics')
  assert.equal(tabFromPath('/sanya/reports'), 'reports')
  assert.equal(tabFromPath('/sanya/'), 'overview')
  assert.equal(tabFromPath('/sanya'), 'overview')
  assert.equal(tabFromPath('/sanya/unknown'), null)
})

test('writes normalized tab path with /sanya base, without hash', () => {
  assert.equal(tabPath('reports'), '/sanya/reports')
  assert.equal(tabPath('unknown'), '/sanya/')
})

test('resolves tabs from modern paths while keeping legacy hash links working', () => {
  assert.equal(tabFromLocation('/sanya/analytics', ''), 'analytics')
  assert.equal(tabFromLocation('/sanya/reports', '#analytics'), 'reports')
  assert.equal(tabFromLocation('/sanya/', '#analytics'), 'analytics')
  assert.equal(tabFromLocation('/sanya/', ''), 'overview')
})

test('restores last active tab from storage when url has no explicit tab', () => {
  assert.equal(resolveInitialTab('/sanya/', '', 'reports'), 'reports')
  assert.equal(resolveInitialTab('/sanya/', '', 'analytics'), 'analytics')
  assert.equal(resolveInitialTab('/sanya/', '', null), 'overview')
  assert.equal(resolveInitialTab('/sanya/special', '', 'reports'), 'special')
  assert.equal(resolveInitialTab('/sanya/', '#reports', 'analytics'), 'reports')
})
