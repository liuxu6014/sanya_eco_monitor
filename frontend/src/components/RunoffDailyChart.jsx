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
const SPLIT_LINE = {
  lineStyle: { color: 'rgba(56, 189, 248, 0.1)', type: 'dotted' },
}

const LEGEND_UNITS = {
  当日累计降雨量: 'mm',
  日均径流: 'm³/min',
  日累计流量: 'm³',
  日均流量: 'm³/s',
  日均流速: 'm/s',
  日均含沙量: 'kg/L',
  日均水位: 'm',
  日均液位压力: 'kPa',
}

function formatLegendNumber(value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const numeric = Number(value)
  return Number.isInteger(numeric) ? String(numeric) : String(numeric)
}

export default function RunoffDailyChart({ data }) {
  const td = data?.data || []
  if (td.length === 0) return <Empty />

  const legendSelected = {
    当日累计降雨量: true,
    日均径流: true,
    日累计流量: true,
    日均流量: true,
    日均流速: true,
    日均含沙量: true,
    日均水位: true,
    日均液位压力: true,
  }

  const latest = td[td.length - 1] || {}
  const legendValueByName = {
    当日累计降雨量: `${formatLegendNumber(latest.rainfall)} ${LEGEND_UNITS.当日累计降雨量}`,
    日均径流: `${formatLegendNumber(latest.runoff_rate)} ${LEGEND_UNITS.日均径流}`,
    日累计流量: `${formatLegendNumber(latest.total_flow)} ${LEGEND_UNITS.日累计流量}`,
    日均流量: `${formatLegendNumber(latest.flow)} ${LEGEND_UNITS.日均流量}`,
    日均流速: `${formatLegendNumber(latest.flow_speed)} ${LEGEND_UNITS.日均流速}`,
    日均含沙量: `${formatLegendNumber(latest.sand)} ${LEGEND_UNITS.日均含沙量}`,
    日均水位: `${formatLegendNumber(latest.water_level)} ${LEGEND_UNITS.日均水位}`,
    日均液位压力: `${formatLegendNumber(latest.liquid_pressure)} ${LEGEND_UNITS.日均液位压力}`,
  }

  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 62, bottom: 28, left: 48, right: 48, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(56, 189, 248, 0.5)',
          width: 2,
          type: 'dashed',
        },
      },
    },
    legend: {
      top: 0,
      left: 'center',
      textStyle: { color: '#b0d8f0', fontSize: 10 },
      icon: 'circle',
      itemGap: 10,
      selected: legendSelected,
      formatter: (name) => `${name}  ${legendValueByName[name] || '—'}`,
    },
    xAxis: {
      type: 'category',
      data: td.map((d) => d.date.slice(5)),
      axisLabel: { ...AXIS_LABEL, interval: 'auto', rotate: 20 },
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.4)' } },
      axisTick: { show: false },
      splitLine: { show: false },
      boundaryGap: true,
    },
    yAxis: [
      {
        type: 'value',
        name: '日均径流 / 日累计流量 / 日均流量 / 日均流速',
        nameLocation: 'end',
        nameGap: 10,
        nameRotate: 0,
        nameTextStyle: { color: '#4ade80', fontSize: 10, fontFamily: CHART_FONT_FAMILY, align: 'left' },
        axisLine: { show: true, lineStyle: { color: '#4ade80' } },
        axisLabel: { ...AXIS_LABEL, color: '#4ade80' },
        splitLine: SPLIT_LINE,
      },
      {
        type: 'value',
        name: '日均水位 / 日均液位压力 / 日均含沙量',
        nameLocation: 'end',
        nameGap: 10,
        nameRotate: 0,
        nameTextStyle: { color: '#facc15', fontSize: 10, fontFamily: CHART_FONT_FAMILY, align: 'right' },
        axisLine: { show: true, lineStyle: { color: '#facc15' } },
        axisLabel: { ...AXIS_LABEL, color: '#facc15' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '当日累计降雨量',
        type: 'bar',
        yAxisIndex: 1,
        z: 2,
        data: td.map((d) => Number(d.rainfall ?? 0)),
        barMaxWidth: 15,
        barMinHeight: 2,
        itemStyle: {
          color: 'rgba(56, 189, 248, 0.3)',
          borderColor: 'rgba(56, 189, 248, 0.75)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
        tooltip: { valueFormatter: (v) => (v != null ? `${Number(v).toFixed(1)} mm` : '—') },
      },
      {
        name: '日均径流',
        type: 'bar',
        yAxisIndex: 0,
        z: 2,
        data: td.map((d) => d.runoff_rate),
        barMaxWidth: 15,
        itemStyle: {
          color: 'rgba(74, 222, 128, 0.34)',
          borderColor: 'rgba(74, 222, 128, 0.8)',
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0],
        },
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m³/min` : '—') },
      },
      {
        name: '日累计流量',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.total_flow),
        lineStyle: { color: '#22c55e', width: 1.5, type: 'dotted' },
        itemStyle: { color: '#22c55e' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m³` : '—') },
      },
      {
        name: '日均流量',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.flow),
        lineStyle: { color: '#4ade80', width: 2 },
        itemStyle: { color: '#4ade80' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m³/s` : '—') },
      },
      {
        name: '日均流速',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: td.map((d) => d.flow_speed),
        lineStyle: { color: '#2dd4bf', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#2dd4bf' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m/s` : '—') },
      },
      {
        name: '日均含沙量',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.sand),
        lineStyle: { color: '#facc15', width: 2 },
        itemStyle: { color: '#facc15' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} kg/L` : '—') },
      },
      {
        name: '日均水位',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.water_level),
        lineStyle: { color: '#fb923c', width: 2 },
        itemStyle: { color: '#fb923c' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} m` : '—') },
      },
      {
        name: '日均液位压力',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: td.map((d) => d.liquid_pressure),
        lineStyle: { color: '#f87171', width: 1.5, type: 'dotted' },
        itemStyle: { color: '#f87171' },
        showSymbol: false,
        tooltip: { valueFormatter: (v) => (v != null ? `${v} kPa` : '—') },
      },
    ],
  }

  return (
    <ResponsiveEChart
      option={option}
      resizeDeps={[td.length]}
      notMerge
      opts={{ renderer: 'canvas' }}
    />
  )
}

function Empty() {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.3)',
        fontSize: 13,
        letterSpacing: 2,
      }}
    >
      暂无数据
    </div>
  )
}
