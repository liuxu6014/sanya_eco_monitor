import { useEffect, useMemo, useState } from 'react'
import ResponsiveEChart from './ResponsiveEChart.jsx'

const TOOLTIP = {
  backgroundColor: 'rgba(3, 17, 46, 0.95)',
  borderColor: 'rgba(56, 189, 248, 0.5)',
  borderWidth: 1,
  textStyle: { color: '#e0f0ff', fontSize: 11 },
  padding: [6, 8],
  confine: true,
}

const CHART_FONT_FAMILY = 'Microsoft YaHei, PingFang SC, Noto Sans CJK SC, Source Han Sans SC, Arial, sans-serif'
const AXIS_LABEL = { color: '#8fc8e8', fontSize: 11, fontFamily: CHART_FONT_FAMILY, hideOverlap: true }
const EMPTY = {
  height: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'rgba(255,255,255,0.3)',
  fontSize: 13,
  letterSpacing: 2,
}

const RUNOFF_LEGEND_UNITS = {
  日累计径流: 'm³',
  日累计流量: 'm³',
  日均流量: 'm³/s',
  日均流速: 'm/s',
  日均含沙量: 'kg/L',
  日均水位: 'm',
  日均液位压力: 'kPa',
}

function formatTooltipMetric(value, unit = '') {
  if (value == null || value === '') return '—'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function formatLegendNumber(value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const numeric = Number(value)
  return Number.isInteger(numeric) ? String(numeric) : String(numeric)
}

function buildDeviceNameMap(deviceMeta = []) {
  return Object.fromEntries(
    (Array.isArray(deviceMeta) ? deviceMeta : [])
      .filter((item) => item?.code)
      .map((item) => [item.code, item.panel_name || item.name || item.short_name || item.code]),
  )
}

function normalizeTabs(overviewRows, deviceRows, deviceMeta) {
  const nameMap = buildDeviceNameMap(deviceMeta)
  const tabs = [{ key: '__overview__', label: '区域总览', rows: overviewRows || [] }]
  Object.keys(deviceRows || {})
    .sort()
    .forEach((code) => {
      tabs.push({ key: code, label: nameMap[code] || code, rows: deviceRows[code] || [] })
    })
  return tabs
}

function normalizeRows(rows) {
  if (Array.isArray(rows)) return rows
  if (Array.isArray(rows?.data)) return rows.data
  return []
}

function buildRainfallOption(rows, title) {
  return {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 48, bottom: 28, left: 48, right: 24, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      formatter: (params) => {
        const list = Array.isArray(params) ? params : [params]
        if (!list.length) return ''
        const axisLabel = list[0]?.axisValueLabel || list[0]?.axisValue || ''
        const lines = list.map((item) => `${item.marker}${item.seriesName}: ${formatTooltipMetric(item.value, 'mm')}`)
        return [axisLabel, ...lines].join('<br/>')
      },
    },
    xAxis: {
      type: 'category',
      data: rows.map((item) => String(item.date || '').slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.4)' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '雨量 (mm)',
      nameLocation: 'end',
      nameGap: 10,
      nameTextStyle: { color: '#60a5fa', fontSize: 10, fontFamily: CHART_FONT_FAMILY, align: 'left' },
      axisLine: { show: true, lineStyle: { color: '#60a5fa' } },
      axisLabel: { ...AXIS_LABEL, color: '#60a5fa' },
      splitLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.1)', type: 'dotted' } },
    },
    series: [
      {
        name: title,
        type: 'bar',
        data: rows.map((item) => Number(item.rainfall ?? 0)),
        barMaxWidth: 18,
        itemStyle: {
          color: 'rgba(56, 189, 248, 0.32)',
          borderColor: 'rgba(56, 189, 248, 0.85)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  }
}

function buildRunoffOption(rows) {
  const latest = rows[rows.length - 1] || {}
  const legendValueByName = {
    日累计径流: `${formatLegendNumber(latest.runoff)} ${RUNOFF_LEGEND_UNITS.日累计径流}`,
    日累计流量: `${formatLegendNumber(latest.total_flow)} ${RUNOFF_LEGEND_UNITS.日累计流量}`,
    日均流量: `${formatLegendNumber(latest.flow)} ${RUNOFF_LEGEND_UNITS.日均流量}`,
    日均流速: `${formatLegendNumber(latest.flow_speed)} ${RUNOFF_LEGEND_UNITS.日均流速}`,
    日均含沙量: `${formatLegendNumber(latest.sand)} ${RUNOFF_LEGEND_UNITS.日均含沙量}`,
    日均水位: `${formatLegendNumber(latest.water_level)} ${RUNOFF_LEGEND_UNITS.日均水位}`,
    日均液位压力: `${formatLegendNumber(latest.liquid_pressure)} ${RUNOFF_LEGEND_UNITS.日均液位压力}`,
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 54, bottom: 28, left: 48, right: 42, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      formatter: (params) => {
        const list = Array.isArray(params) ? params : [params]
        if (!list.length) return ''
        const axisLabel = list[0]?.axisValueLabel || list[0]?.axisValue || ''
        const lines = list.map((item) => `${item.marker}${item.seriesName}: ${formatTooltipMetric(item.value, RUNOFF_LEGEND_UNITS[item.seriesName] || '')}`)
        return [axisLabel, ...lines].join('<br/>')
      },
    },
    legend: {
      top: 0,
      left: 'center',
      textStyle: { color: '#b0d8f0', fontSize: 10 },
      icon: 'circle',
      itemGap: 10,
      formatter: (name) => `${name}  ${legendValueByName[name] || '—'}`,
    },
    xAxis: {
      type: 'category',
      data: rows.map((item) => String(item.date || '').slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.4)' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: '日累计径流 / 日累计流量 / 日均流量 / 日均流速',
        nameLocation: 'end',
        nameGap: 10,
        nameTextStyle: { color: '#4ade80', fontSize: 10, fontFamily: CHART_FONT_FAMILY, align: 'left' },
        axisLine: { show: true, lineStyle: { color: '#4ade80' } },
        axisLabel: { ...AXIS_LABEL, color: '#4ade80' },
        splitLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.1)', type: 'dotted' } },
      },
      {
        type: 'value',
        name: '日均含沙量 / 日均水位 / 日均液位压力',
        nameLocation: 'end',
        nameGap: 10,
        nameTextStyle: { color: '#facc15', fontSize: 10, fontFamily: CHART_FONT_FAMILY, align: 'right' },
        axisLine: { show: true, lineStyle: { color: '#facc15' } },
        axisLabel: { ...AXIS_LABEL, color: '#facc15' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '日累计径流',
        type: 'bar',
        yAxisIndex: 0,
        data: rows.map((item) => Number(item.runoff ?? 0)),
        barMaxWidth: 14,
        itemStyle: {
          color: 'rgba(74, 222, 128, 0.34)',
          borderColor: 'rgba(74, 222, 128, 0.8)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: '日累计流量',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: rows.map((item) => item.total_flow),
        lineStyle: { color: '#22c55e', width: 1.5, type: 'dotted' },
        itemStyle: { color: '#22c55e' },
        showSymbol: false,
      },
      {
        name: '日均流量',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: rows.map((item) => item.flow),
        lineStyle: { color: '#38bdf8', width: 2 },
        itemStyle: { color: '#38bdf8' },
        showSymbol: false,
      },
      {
        name: '日均流速',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: rows.map((item) => item.flow_speed),
        lineStyle: { color: '#2dd4bf', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#2dd4bf' },
        showSymbol: false,
      },
      {
        name: '日均含沙量',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: rows.map((item) => item.sand),
        lineStyle: { color: '#facc15', width: 2 },
        itemStyle: { color: '#facc15' },
        showSymbol: false,
      },
      {
        name: '日均水位',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: rows.map((item) => item.water_level),
        lineStyle: { color: '#fb923c', width: 1.5 },
        itemStyle: { color: '#fb923c' },
        showSymbol: false,
      },
      {
        name: '日均液位压力',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: rows.map((item) => item.liquid_pressure),
        lineStyle: { color: '#f87171', width: 1.5, type: 'dotted' },
        itemStyle: { color: '#f87171' },
        showSymbol: false,
      },
    ],
  }
}

function buildOption(mode, rows, title) {
  if (mode === 'rainfall') return buildRainfallOption(rows, title)
  return buildRunoffOption(rows)
}

export default function DeviceSeriesExplorer({
  rainfallOverview,
  rainfallByDevice,
  rainfallAnomalySummary,
  runoffOverview,
  runoffByDevice,
  runoffAnomalySummary,
  deviceMeta,
  allowedModes = ['rainfall', 'runoff'],
  defaultMode = allowedModes[0] ?? 'rainfall',
}) {
  const rainfallDeviceMeta = deviceMeta?.rain_gauges || []
  const runoffDeviceMeta = deviceMeta?.runoff_devices || []
  const [mode, setMode] = useState(defaultMode)
  const [activeKey, setActiveKey] = useState('__overview__')

  const tabs = useMemo(
    () => normalizeTabs(
      mode === 'rainfall' ? rainfallOverview : runoffOverview,
      mode === 'rainfall' ? rainfallByDevice : runoffByDevice,
      mode === 'rainfall' ? rainfallDeviceMeta : runoffDeviceMeta,
    ),
    [mode, rainfallOverview, rainfallByDevice, runoffOverview, runoffByDevice, rainfallDeviceMeta, runoffDeviceMeta],
  )

  useEffect(() => {
    if (!allowedModes.includes(mode)) {
      setMode(defaultMode)
      setActiveKey('__overview__')
    }
  }, [allowedModes, defaultMode, mode])

  useEffect(() => {
    if (!tabs.some((item) => item.key === activeKey)) {
      setActiveKey('__overview__')
    }
  }, [activeKey, tabs])

  const activeTab = tabs.find((item) => item.key === activeKey) || tabs[0]
  const rows = normalizeRows(activeTab?.rows)
  const anomalySummaryForMode = mode === 'rainfall' ? rainfallAnomalySummary : runoffAnomalySummary
  const showModeSwitcher = allowedModes.length > 1

  if (!tabs.length || !rows.length) {
    return <div style={EMPTY}>暂无设备维度数据</div>
  }

  const option = buildOption(mode, rows, activeTab.label)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
      {showModeSwitcher ? (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {[
            { key: 'rainfall', label: '雨量设备' },
            { key: 'runoff', label: '径流设备' },
          ].filter((item) => allowedModes.includes(item.key)).map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => { setMode(item.key); setActiveKey('__overview__') }}
              style={{
                padding: '6px 12px',
                borderRadius: 999,
                border: mode === item.key ? '1px solid rgba(56, 189, 248, 0.7)' : '1px solid rgba(125, 211, 252, 0.14)',
                background: mode === item.key ? 'rgba(56, 189, 248, 0.14)' : 'rgba(7, 21, 44, 0.62)',
                color: mode === item.key ? '#dff4ff' : '#8fb6da',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {tabs.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setActiveKey(item.key)}
            style={{
              padding: '4px 10px',
              borderRadius: 999,
              border: activeKey === item.key ? '1px solid rgba(96, 165, 250, 0.88)' : '1px solid rgba(125, 211, 252, 0.14)',
              background: activeKey === item.key ? 'rgba(37, 99, 235, 0.18)' : 'rgba(7, 21, 44, 0.55)',
              color: activeKey === item.key ? '#f8fbff' : '#92b8db',
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {anomalySummaryForMode?.has_anomaly ? (
        <div
          style={{
            borderRadius: 12,
            border: '1px solid rgba(248, 113, 113, 0.35)',
            background: 'rgba(127, 29, 29, 0.18)',
            color: '#fecaca',
            padding: '8px 12px',
            fontSize: 12,
            lineHeight: 1.6,
          }}
        >
          {anomalySummaryForMode.message || '已检测到异常值，当前展示为设备原始值，未做过滤。'}
        </div>
      ) : null}

      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveEChart option={option} resizeDeps={[mode, activeKey, rows.length]} notMerge opts={{ renderer: 'canvas' }} />
      </div>
    </div>
  )
}
