import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const read = (rel) => readFileSync(resolve(here, rel), 'utf8')

test('special analysis registers the device maintenance section and panel', () => {
  const page = read('../src/components/SpecialAnalysisPage.jsx')
  assert.match(page, /key:\s*'maintenance',\s*label:\s*'设备运维'/)
  assert.match(page, /import DeviceMaintenancePanel from '\.\/DeviceMaintenancePanel\.jsx'/)
  assert.match(page, /<DeviceMaintenancePanel\s+active=/)
  assert.match(page, /section === 'maintenance'/)
})

test('api exposes maintenance endpoints and export url helper', () => {
  const apiSrc = read('../src/utils/api.js')
  assert.match(apiSrc, /maintenanceDevices:\s*\(\)\s*=>\s*get\('\/maintenance\/devices'\)/)
  assert.match(apiSrc, /maintenanceOutages:/)
  assert.match(apiSrc, /export function maintenanceExportUrl/)
  assert.match(apiSrc, /\/maintenance\/outages\/export/)
})

test('device types util defines labels and low-frequency set', () => {
  const util = read('../src/utils/deviceTypes.js')
  assert.match(util, /runoff:\s*'径流'/)
  assert.match(util, /rain:\s*'雨量'/)
  assert.match(util, /LOW_FREQ_TYPES/)
  assert.match(util, /export function deviceLabel/)
})

test('maintenance panel renders per-device + detail tables and stats', () => {
  const panel = read('../src/components/DeviceMaintenancePanel.jsx')
  // 自定义控件已接入
  assert.match(panel, /import DeviceSelect from '\.\/DeviceSelect\.jsx'/)
  assert.match(panel, /import DateRangePicker from '\.\/DateRangePicker\.jsx'/)
  // 明细表列
  for (const col of ['设备名称', '异常开始时间', '异常结束时间', '持续时长']) {
    assert.ok(panel.includes(col), `panel should include column ${col}`)
  }
  // 各设备统计表
  assert.match(panel, /各设备掉线统计/)
  assert.match(panel, /近7天异常次数/)
  assert.match(panel, /近30天异常次数/)
  assert.match(panel, /当前掉线/)
  assert.match(panel, /导出 Excel/)
  assert.match(panel, /formatRowDuration\(row\.duration_seconds,\s*row\.device_type\)/)
  assert.match(panel, /仅识别连续多日掉线/)
  // 明细表分页
  assert.match(panel, /pagedRows/)
  assert.match(panel, /上一页/)
  assert.match(panel, /下一页/)
  assert.match(panel, /每页/)
  assert.match(panel, /第 \{pageSafe\} \/ \{totalPages\} 页/)
})

test('custom device select shows "全部设备" and type chips', () => {
  const select = read('../src/components/DeviceSelect.jsx')
  assert.match(select, /全部设备/)
  assert.match(select, /import TypeChip from '\.\/TypeChip\.jsx'/)
  assert.match(select, /onChange\?\.\(/)
})

test('custom date range picker provides presets and a calendar', () => {
  const picker = read('../src/components/DateRangePicker.jsx')
  assert.match(picker, /近7天/)
  assert.match(picker, /近30天/)
  assert.match(picker, /WEEKDAYS/)
  assert.match(picker, /onChange\?\.\([^)]*format\('YYYY-MM-DD'\)/)
})
