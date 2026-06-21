import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

function read(relativePath) {
  return fs.readFileSync(path.resolve(__dirname, relativePath), 'utf8')
}

test('overview panels read unified device_meta instead of local hardcoded maps', () => {
  const rainPanel = read('../src/components/RainGaugePanel.jsx')
  const runoffPanel = read('../src/components/RunoffPanel.jsx')
  const explorer = read('../src/components/DeviceSeriesExplorer.jsx')
  const app = read('../src/App.jsx')
  const specialAnalysisPage = read('../src/components/SpecialAnalysisPage.jsx')

  assert.match(rainPanel, /deviceMeta/)
  assert.doesNotMatch(rainPanel, /const DEVICE_MAP =/)
  assert.doesNotMatch(rainPanel, /const displayCodes = \[/)

  assert.match(runoffPanel, /deviceMeta/)
  assert.doesNotMatch(runoffPanel, /const DEVICE_NAMES =/)
  assert.doesNotMatch(runoffPanel, /const ALL_CODES = \[/)

  assert.match(explorer, /deviceMeta/)
  assert.doesNotMatch(explorer, /const RAIN_DEVICE_NAMES =/)
  assert.doesNotMatch(explorer, /const RUNOFF_DEVICE_NAMES =/)

  assert.match(app, /deviceMeta=\{overview\.data\?\.data\?\.device_meta\?\.rain_gauges\}/)
  assert.match(app, /deviceMeta=\{overview\.data\?\.data\?\.device_meta\?\.runoff_devices\}/)
  assert.match(specialAnalysisPage, /deviceMeta=\{\{\s*rain_gauges:\s*overviewDeviceMeta\?\.rain_gauges\s*\}\}/)
  assert.match(specialAnalysisPage, /deviceMeta=\{\{\s*runoff_devices:\s*overviewDeviceMeta\?\.runoff_devices\s*\}\}/)
})

test('rain gauge panel labels overview rainfall as realtime rainfall', () => {
  const rainPanel = read('../src/components/RainGaugePanel.jsx')
  assert.match(rainPanel, /实时雨量/)
  assert.doesNotMatch(rainPanel, /今日累计雨量/)
})

test('runoff panel restores cumulative total-flow label and only shows rainfall metric when available', () => {
  const runoffPanel = read('../src/components/RunoffPanel.jsx')
  assert.match(runoffPanel, /累计流量/)
  assert.doesNotMatch(runoffPanel, /设备累计读数/)
  assert.match(runoffPanel, /今日累计降雨量/)
  assert.match(runoffPanel, /showRainfallMetric/)
})

test('map center reads backend-provided device metadata instead of local DEVICES constant', () => {
  const mapCenter = read('../src/components/MapCenter.jsx')

  assert.match(mapCenter, /deviceMeta/)
  assert.doesNotMatch(mapCenter, /const DEVICES = \[/)
  assert.match(mapCenter, /实时雨量/)
})
