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

test('reads tab from path', () => {
  assert.equal(tabFromPath('/analytics'), 'analytics')
  assert.equal(tabFromPath('/reports'), 'reports')
  assert.equal(tabFromPath('/'), 'overview')
  assert.equal(tabFromPath('/unknown'), null)
})

test('writes normalized tab path without hash', () => {
  assert.equal(tabPath('reports'), '/reports')
  assert.equal(tabPath('unknown'), '/')
})

test('resolves tabs from modern paths while keeping legacy hash links working', () => {
  assert.equal(tabFromLocation('/analytics', ''), 'analytics')
  assert.equal(tabFromLocation('/reports', '#analytics'), 'reports')
  assert.equal(tabFromLocation('/', '#analytics'), 'analytics')
  assert.equal(tabFromLocation('/', ''), 'overview')
})

test('restores last active tab from storage when url has no explicit tab', () => {
  assert.equal(resolveInitialTab('/', '', 'reports'), 'reports')
  assert.equal(resolveInitialTab('/', '', 'analytics'), 'analytics')
  assert.equal(resolveInitialTab('/', '', null), 'overview')
  assert.equal(resolveInitialTab('/special', '', 'reports'), 'special')
  assert.equal(resolveInitialTab('/', '#reports', 'analytics'), 'reports')
})
